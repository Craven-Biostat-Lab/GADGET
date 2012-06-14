#!/usr/bin/python
"""
Grab rows from the "abstract" database table with no "indexed_date", and put
them in the index.  Optimize the index when we're done.
"""

import MySQLdb
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, IDLIST, DATETIME, STORED, BOOLEAN
from datetime import datetime

# this is the path to the index directory.
ABSTRACT_INDEX_PATH = '../index'

# connect to the database
db = MySQLdb.connect(user='root', passwd='password', db='new')
c = db.cursor() # cursor for grabbing abstracts
c_update = db.cursor() # seperate cursor for updating "indexed" field
c_genes = db.cursor() # cursor for fetching associated genes

# unicode stuff
db.set_character_set('utf8')
c.execute('SET NAMES utf8;')
c.execute('SET CHARACTER SET utf8;')
c.execute('SET character_set_connection=utf8;')


# open or create the index
if index.exists_in(ABSTRACT_INDEX_PATH):
    ix = index.open_dir(ABSTRACT_INDEX_PATH)
else:
    # define the index fields
    class Schema(SchemaClass):
        pmid = NUMERIC(stored=True, unique=True, signed=False)
        genes = IDLIST(stored=True) # Entrez ID's
        homolog_genes = IDLIST(stored=True) # Entrez ID's
        title = TEXT(stored=True)
        abstract = TEXT
        authors = TEXT(stored=True)
        pubdate = DATETIME(stored=True)
        year = NUMERIC(stored=True)
        review = BOOLEAN(stored=True)
        journal = STORED
        volume = STORED
        pages = STORED
        
    ix = index.create_in(ABSTRACT_INDEX_PATH, Schema)

# get unindexed and updated abstracts
c.execute("""
    select `pubmed_id`, `title`, `abstract`, `authors`, `pubdate`, year(`pubdate`), `journal`, `volume`, `pages`, `review`
    from `abstract`
    where `updated` is not null
    and (`indexed` is null or `indexed` < `updated`);
    """)

# update the index with the articles
writer = ix.writer()
for i, article in enumerate(c):
    pmid, title, abstract, authors, pubdate, year, journal, volume, pages, review = article
    

    # make text fields unicode
    if title is not None:
        title = unicode(title, 'utf-8')
    if abstract is not None:
        abstract = unicode(abstract, 'utf-8')
    if authors is not None:
        authors = unicode(authors, 'utf-8')


    
    # get associated genes
    c_genes.execute("""
        SELECT `gene` 
        from `gene_abstract` 
        where `abstract` = %s
        """, (pmid,))
    genes = u' '.join([unicode(g[0]) for g in c_genes.fetchall()])
        
    c_genes.execute("""
        SELECT `gene` 
        from `homologene_gene_abstract` 
        where `abstract` = %s
        """, (pmid,))
    homolog_genes = u' '.join([unicode(g[0]) for g in c_genes.fetchall()]) 
    
    # change the date to a datetime
    if pubdate:
        pubdate = datetime.fromordinal(pubdate.toordinal())
    
    # index the document
    writer.update_document(pmid=pmid, genes=genes, homolog_genes=homolog_genes,
        title=title, abstract=abstract, authors=authors, pubdate=pubdate, 
        year=year, journal=journal, volume=volume, pages=pages, review=review)
    
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
