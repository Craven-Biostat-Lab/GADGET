#!/usr/bin/python
"""
Grab rows from the "abstract" database table that need to be indexed (updated 
but not indexed, or 'indexed' date is older than 'index_dirty' date), and put
them in the index.  Optimize the index when we're done.
"""

import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, IDLIST, DATETIME, STORED, BOOLEAN
from datetime import datetime
from shutil import rmtree
import os.path
from os import mkdir

from config import ABSTRACT_INDEX_PATH, TEMP_METABOLITE_INDEX_PATH, getcursor

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
                metabolites = IDLIST(stored=True) # HMDB ID's
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


def lookup_metabolites(pmid, cursor):
    """Find metabolites tied to an abstract in the metabolite_abstract table"""
    
    cursor.execute("""
    SELECT `metabolite_hmdb_id` 
    from `metabolite_abstract` 
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


def write(articles, ix, db, mark_db=True):
    """
    Given a list of articles as tuples, write them to the index ix.
    
    If mark_db is True, then update the database record for each article in 'articles,'
    recording that it has been indexed.
    """ 

    logger.debug('writing articles to index')

    # update the index with the articles
    writer = ix.writer()
    
    # keep track of the articles we've written so far, so we cam mark them as
    # indexed after a successful commit
    writtenPMIDs = []

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
        
        metabolites = u' '.join([unicode(g[0]) for g in lookup_metabolites(pmid, c)])
        
        # index the document
        writer.update_document(pmid=pmid, genes=genes, homolog_genes=homolog_genes,
            metabolites=metabolites,
            title=title, abstract=abstract, authors=authors, year=year, month=month, 
            day=day, journal=journal, volume=volume, pages=pages, review=review)
        
        # keep track of the articles we've written so far.
        writtenPMIDs.append(pmid)
        
        # commit the index every 100,000 articles
        if i % 100000 == 0 and i != 0:
            writer.commit(merge=False)
            writer = ix.writer()
            logger.debug('Commiting abstract index.  Abstracts: %s', i)
            
    logger.info('wrote articles to index')


    logger.debug("committing abstract index...")
    writer.commit(merge=False) 
    logger.info("committed abstract index")


    # mark all of the indexed abstracts as indexed after a successful commit
    if mark_db:
        for pmid in writtenPMIDs:
            mark_as_indexed(pmid, c)

    c.close()


def remove_bad_abstracts(ix, db):
    """Remove abatracts in the "removed_abstracts" database table from the
    index."""

    c = getcursor(db)

    # get abstract PMIDs from the removed_abstract table
    c.execute("""
    select `abstract` from `removed_abstracts`
    """)

    logger.debug('Removing abstracts in the `removed_abstracts` table from the index')

    # for each PMID in the query result, try to delete that abstract from
    # the index.
    writer = ix.writer()
    for row in c:
        pmid = row[0]

        writer.delete_by_term('pmid', unicode(pmid))
    
    c.close()
    logger.info('Removed abstracts in the `removed_abstracts` table from the index')


def update_index(db):
    """Find abstracts in the database that need to be updated, and update them
    in the index."""
    ix = open_index(ABSTRACT_INDEX_PATH)

    logger.debug('Writing articles to index')

    try:
        write(articles(db), ix, db)
    except Exception as e:
        logger.critical('could not write articles to index.  Error message: %s', e)
        raise

    logger.info('Wrote articles to index')

    try:
        remove_bad_abstracts(ix, db)
    except Exception as e:
        logger.error('could not remove abstracts in the `removed_abstracts` table from the index.  Error message: %s', e)

    ix.close()
    
    
    
    


def temp_metabolite_index(db):
    """Create a temporary index containing only the new articles, so we can 
    scan them for metabolites."""


    # remove existing index
    if os.path.exists(TEMP_METABOLITE_INDEX_PATH):
        rmtree(TEMP_METABOLITE_INDEX_PATH)
    
    try:
        mkdir(TEMP_METABOLITE_INDEX_PATH)
    except Exception as e:
	logger.critical('could not make dir')

    ix = open_index(TEMP_METABOLITE_INDEX_PATH)
    
    logger.debug('Creating temporary index for metabolite scanning')
    
    try:
        write(articles(db), ix, db, mark_db=False)
    except Exception as e:
        logger.critical('could not write articles to temporary metabolite-scanning index.  Error message: %s', e)
        raise

    ix.close()

    


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
        logger.warning('database abstract count does not match index abstract count.  database count: %s, index count: %s.  There may have been an error committing the index, or an abstract was removed from the abstract table.  If you can\'t figure out what caused the inconsistency, one way to fix it is to re-build the index from scratch (delete the contents of the index folder, set the `indexed` column in the `abstract` table to null for all rows, and run the updater script.  It will probably take a couple hours.', db_count, ix_count)
        return False
