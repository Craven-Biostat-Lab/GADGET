#!/usr/bin/python
"""
Grab rows from the "abstract" database table that need to be indexed (updated 
but not indexed, or 'indexed' date is older than 'index_dirty' date), and put
them in the index.  Optimize the index when we're done.
"""

import MySQLdb
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, IDLIST, DATETIME, STORED, BOOLEAN
from datetime import datetime

from config import ABSTRACT_INDEX_PATH, getcursor

# set up logging
import logging
logger = logging.getLogger('GADGET.updater.buildindex')


def open_index(indexpath):
    """Open and return a Whoosh index in the given path"""    

    logger.debug('opening index to update abstracts')

    # open or create the index
    # use numners to represent a date instead of a DATETIME object because we're
    # missing a lot of data, and Datetime's must have a year, month, and day.
    try:
        if index.exists_in(indexpath):
            ix = index.open_dir(indexpath)
        else:
            # define the index fields
            class Schema(SchemaClass):
                pmid = NUMERIC(stored=True, unique=True, signed=False)
                genes = IDLIST(stored=True) # Entrez ID's
                homolog_genes = IDLIST(stored=True) # Entrez ID's
                title = TEXT(stored=True)
                abstract = TEXT
                authors = TEXT(stored=True)
                year = NUMERIC(stored=True)
                month = NUMERIC(stored=True)
                day = NUMERIC(stored=True)
                review = BOOLEAN(stored=True)
                journal = STORED
                volume = STORED
                pages = STORED
                
            ix = index.create_in(indexpath, Schema)
    except Exception as e:
        logger.critical('Could not open index in %s,  Error message: %s', indexpath, e)
        raise

    logger.info('opened index to update abstracts')

    return ix


def articles(db):
    # get unindexed and updated abstracts

    logger.debug('Looking up articles that need to be indexed')

    c = getcursor(db)

    try:
        c.execute("""
            select `pubmed_id`, `title`, `abstract`, `authors`, year(`pubdate`), month(`pubdate`), day(`pubdate`), `journal`, `volume`, `pages`, `review`
            from `abstract`
            where `updated` is not null
            and (`indexed` is null or `indexed` < `updated` or `indexed` < `index_dirty`);
            """)
    except Exception as e:
        logger.critical('Could not look up articles that need to be indexed.  Error message: %s', e)
        raise

    logger.info('Looked up articles that need to be indexed')

    for article in c:
        yield article

    c.close()


def lookup_genes(pmid, cursor):
    """Find genes tied to an abstract in the gene_abstract table"""

    cursor.execute("""
    SELECT `gene` 
    from `gene_abstract` 
    where `abstract` = %s
    """, (pmid,))

    return cursor.fetchall()


def lookup_homolog_genes(pmid, cursor):
    """Find genes tied to an abstract in the homologene_gene_abstract table"""

    cursor.execute("""
    SELECT `gene` 
    from `homologene_gene_abstract` 
    where `abstract` = %s
    """, (pmid,))

    return cursor.fetchall()


def mark_as_indexed(pmid, cursor):
    """Mark an abstract as indexed"""

    cursor.execute("""
    update `abstract`
    set `indexed` := now()
    where pubmed_id = %s
    """, (pmid,))


def write(articles, ix, db):
    """Given a list of articles as tuples, write them to the index ix.""" 

    logger.debug('writing articles to index')

    # update the index with the articles
    writer = ix.writer()
    
    c = getcursor(db)

    for i, article in enumerate(articles):
        pmid, title, abstract, authors, year, month, day, journal, volume, pages, review = article
        

        # make text fields unicode
        if title is not None:
            title = unicode(title, 'utf-8')
        if abstract is not None:
            abstract = unicode(abstract, 'utf-8')
        if authors is not None:
            authors = unicode(authors, 'utf-8')


        # get associated genes
        genes = u' '.join([unicode(g[0]) for g in lookup_genes(pmid, c)])
            
        homolog_genes = u' '.join([unicode(g[0]) for g in lookup_homolog_genes(pmid, c)]) 
        
        # index the document
        writer.update_document(pmid=pmid, genes=genes, homolog_genes=homolog_genes,
            title=title, abstract=abstract, authors=authors, year=year, month=month, 
            day=day, journal=journal, volume=volume, pages=pages, review=review)
        
        # mark the document as indexed
        mark_as_indexed(pmid, c)
        
        # commit the index every 100,000 articles
        if i % 100000 == 0 and i != 0:
            writer.commit(merge=False)
            writer = ix.writer()
            logger.debug('Commiting abstract index.  Abstracts: %s', i)
            
    logger.info('wrote articles to index')

    logger.info("committing and merging abstract index...")
    writer.commit(optimize=True) # Merge everything.  This will take a long time.
    logger.info("committed and merged abstract index")
    c.close()


def update_index(db):
    ix = open_index(ABSTRACT_INDEX_PATH)

    logger.debug('Writing articles to index')

    try:
        write(articles(db), ix, db)
    except Exception as e:
        logger.critical('could not write articles to index.  Error message: %s', e)
        raise

    ix.close()

    logger.info('Wrote articles to index')
    

def check_abstract_counts(db):
    """Check to see if the index and database table have the same number of
    abstracts (something is wrong if they don't.)"""
    
    # get index abstract count
    ix = open_index(ABSTRACT_INDEX_PATH)
    ix_count = ix.doc_count()
    ix.close()

    # get abstract count from database
    c = getcursor(db)

    c.execute("""
    select count(*) from `abstract`
    """)

    db_count, = c.fetchone()
    c.close()

    if ix_count == db_count:
        logger.info('database abstract count matches index abstract count (this is good.)  abstract count: %s', ix_count)
        return True
    else:
        logger.warning('database abstract count does not match index abstract count.  database count: %s, index count: %s.  There may have been an error committing the index, or an abstract was removed from the abstract table.  If you can\'t figure out what caused the inconsistency, one way to fix it is to re-build the index from scratch (delete the contents of the index folder, set the `indexed` column in the `abstract` table to null for all rows, and run the updater script.  It will probably take a couple hours.')
    return False