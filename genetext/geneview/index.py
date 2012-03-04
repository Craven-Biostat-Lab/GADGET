#!/usr/bin/python
import atexit
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC
from whoosh.qparser import MultifieldParser
from whoosh.query import And, Term, ConstantScoreQuery, NullQuery
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

# query parser and searcher
parser = MultifieldParser(fieldnames=('title', 'abstract'), schema=ix.schema)
searcher = ix.searcher(weighting=Frequency)

def get_abstracts_old(query):
    """Return a list of Pubmed ID's for abstracts matching the given query."""
    
    # first check the cache to see if we've done this seach already
    cached = cache.get('q_' + query.replace(' ', '_'))
    if cached:
        #print 'Found it in the cache!', query, len(cached)
        return cached
        
    else:
        # parse the user's query
        q = parser.parse(unicode(query))
        
        # get the query results
        results = [r['pmid'] for r in searcher.search(q, limit=None)]
        
        # remember the results for 10 * 60 seconds
        cache.set('q_' + query.replace(' ', '_'), results, 600) # remember the results for 10 * 60 seconds
        
        return results


def cachekey(keywords='', genes=[], genehomologs=True):
    """Return a key to use for cached query results"""
    
    if genes is None:
        genes = []
    
    return 'query_k:{0}_g:{1}_h:{2}'.format(
        keywords.replace(' ', '_'),
        ','.join(str(g) for g in genes),
        genehomologs)


def buildquery(keywords=None, genes=None, genehomologs=True):
    """Return a whoosh query object for searching the index"""
    
    # decide which index field to use for genes, based upon whether we're
    # using homologs
    genefield = 'homolog_genes' if genehomologs else 'genes'
    
    # build gene branch of query
    if genes is not None:   
        genebranch = And([Term(genefield, unicode(g)) for g in genes])
    else:
        genebranch = NullQuery()
        
    # get keyword branch of query
    keywordbranch = parser.parse(unicode(keywords))

    # return query, don't score each abstract
    return ConstantScoreQuery(genebranch & keywordbranch)

def get_abstracts(keywords=None, genes=None, genehomologs=True):
    
    # return an empty list if we don't have a query or list of genes
    if keywords is None and genes is None:
        return []
    
    # check to see if we've done this search already
    # return the cached results if the query is in the cache
    key = cachekey(keywords, genes, genehomologs)
    cached = cache.get(key)
    if cached:
        return cached
    
    query = buildquery(keywords, genes, genehomologs)
    
    # search the index
    results = [r['pmid'] for r in searcher.search(query, limit=None)]
    
    # remember the results for 10 * 60 seconds
    #cache.set('q_' + query.replace(' ', '_'), results, 600) # remember the results for 10 * 60 seconds
    cache.set(key, results, 600)
    
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
