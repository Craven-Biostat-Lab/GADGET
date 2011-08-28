#!/usr/bin/python
import atexit
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC
from whoosh.qparser import MultifieldParser
from whoosh.scoring import Frequency

try:
    from genetext.settings import ABSTRACT_INDEX_PATH
    from django.core.cache import cache
except ImportError:
    ABSTRACT_INDEX_PATH = '/home/genetext/genetext/index'

# open or create the index
if index.exists_in(ABSTRACT_INDEX_PATH):
    ix = index.open_dir(ABSTRACT_INDEX_PATH)
else:
    # define the index fields
    class Schema(SchemaClass):
        pmid = NUMERIC(stored=True, unique=True, signed=False)
        title = TEXT
        abstract = TEXT
        year = NUMERIC
        
    ix = index.create_in(ABSTRACT_INDEX_PATH, Schema)

def updateIndex():
    """
    Do not expose this method to the web interface.
    
    Grab rows from the "abstract" database table with no "indexed_date", and put
    them in the index.  Use MySQLdb instead of the Django database layer, because
    Django doesn't know about the abstract table. 
    """
    
    # connect to the database
    import MySQLdb
    db = MySQLdb.connect(user='root', passwd='password', db='genetext')
    c = db.cursor() # cursor for grabbing abstracts
    c_update = db.cursor() # seperate cursor for updating "indexed" field
    
    # get unindexed and updated abstracts
    c.execute("""
        select `pubmed_id`, `title`, `abstract`, `year`
        from `abstract`
        where `updated` is not null
        and (`indexed` is null or `indexed` < `updated`);
        """)
    
    # update the index with the articles
    writer = ix.writer()
    for i, article in enumerate(c):
        pmid, title, abstract, year = article
        
        # For some reason, some of the abstracts are encoded in utf-8, and some 
        # in latin-1.  This is gross, but it works.
        if title is not None:
            try:
                title = unicode(title, 'utf-8')
            except UnicodeDecodeError:
                title = unicode(title, 'latin-1')
        if abstract is not None:
            try:
                abstract = unicode(abstract, 'utf-8')
            except UnicodeDecodeError:
                abstract = unicode(abstract, 'latin-1')
        
        writer.update_document(pmid=pmid, title=title, 
            abstract=abstract, year=year)
        
        # mark the document as indexed
        c_update.execute("""
            update `abstract`
            set `indexed` := now()
            where pubmed_id = %s
            """, (pmid,))
        
        # commit the index every 10,000 articles
        if i % 10000 == 0:
            writer.commit(merge=False)
            writer = ix.writer()
            print 'Commit.  Abstracts:', i
    writer.commit(optimize=True) # Merge everything.  This will take a long time.
    
    c.close()
    c_update.close()
    db.close()

def get_abstracts(query):
    """Return a list of Pubmed ID's for abstracts matching the given query."""
    
    # first check the cache to see if we've done this seach already
    cached = cache.get('q_' + query.replace(' ', '_'))
    if cached:
        print 'Found it in the cache!', query, len(cached)
        
        return cached
        
    else:
        # parse the user's query
        parser = MultifieldParser(fieldnames=('title', 'abstract'), schema=ix.schema)
        q = parser.parse(unicode(query))
        
        # get the query results
        with ix.searcher(weighting=Frequency) as searcher:
            results = [r['pmid'] for r in searcher.search(q, limit=None)]
            
            cache.set('q_' + query.replace(' ', '_'), results, 600) # remember the results for 10 * 60 seconds
            return results
    

def corpus_size():
    """Return the number of abstracts in the corpus"""
    return ix.doc_count()

@atexit.register
def close(): # close the index when the module is unloaded
    ix.close()

if __name__ == '__main__':
    print 'Updating the index...'
    updateIndex()
