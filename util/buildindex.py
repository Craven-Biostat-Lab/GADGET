#!/usr/bin/python
"""
Grab rows from the "abstract" database table with no "indexed_date", and put
them in the index.  Optimize the index when we're done.
"""

import MySQLdb
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC

# this is the path to the index directory.
ABSTRACT_INDEX_PATH = '../index'

# connect to the database
db = MySQLdb.connect(user='root', passwd='password', db='genetext')
c = db.cursor() # cursor for grabbing abstracts
c_update = db.cursor() # seperate cursor for updating "indexed" field


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
