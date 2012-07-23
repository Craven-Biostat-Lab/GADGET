#!/usr/bin/python
"""
Update the gene-abstract links and abstract texts that GADGET uses.

This script will insert records into these database tables.  These tables can 
be empty when you run the script:
abstract
gene_abstract
homologene_gene_abstract
mgi_reference
removed_abstracts

The script will update the `abstracts` and `homolog_abstracts` of the `gene`
table, but will not insert any records.  The `gene` table should be populated 
before you run the script.

The script also uses the following tables, but does not make any changes:
homologene_gene
mgi_entrez_gene
sgd_xrefs

Briefly, the script downloads and decompresses files specified in "config.py",
inserts their contents into the `gene_abstract` table, fetches new abstracts
from PubMed, and updates the index of abstracts.
"""


import load_gene_abstract_links 
import abstractqueries
import fetchabstracts
import buildindex

from config import dbparams, logfilename, loglevel

# set up logging
import logging
import logging.handlers

logger = logging.getLogger('GADGET.updater')
logger.setLevel(logging.DEBUG)

fh = logging.handlers.RotatingFileHandler(logfilename, maxBytes=5000, backupCount=5)
fh.setLevel(getattr(logging, loglevel.upper()))
formatter = logging.Formatter('%(levelname)s - %(filename)s - line: %(lineno)s - %(asctime)s\n    %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)



# set up database connection
try:
    import MySQLdb
    db = MySQLdb.connect(**dbparams)

    # unicode stuff
    db.set_character_set('utf8')
except Exception as e:
    logger.critical('Error connecting to database.  Error message: %s', e)
    raise


if __name__ == '__main__':
    
    logger.info('Beginning GADGET data update.  Updating gene-abstract links and abstract texts.')

    # 1: get new gene_abstract links from gene2pubmed, MGI, SGD, etc.
    load_gene_abstract_links.loadall(db)
    load_gene_abstract_links.cleanup(db)

    # 2: 'mark dirty abstracts' trigger set 'dirty_indexed' column to now()
    # for abstracts with new gene-abstract links

    # 3: add new abstracts from 'gene_abstract' links to 'abstract' table
    abstractqueries.add_new_abstracts(db)

    # 4: add abstracts with more than 1000 genes to 'removed_abstract' table
    abstractqueries.find_too_many_genes(db)

    # 5: remove abstracts in 'removed_abstract' table from 'abstract' table
    abstractqueries.remove_bad_abstracts(db)

    # 6: fetch new abstracts from PubMed
    fetchabstracts.fetchall(db)

    # 7: add abstracts that couldn't be fetched to 'removed_abstract' table
    abstractqueries.find_unfetched_abstracts(db)

    # 8: remove abstracts in 'removed_abstract' table from 'abstract' table
    abstractqueries.remove_bad_abstracts(db)

    # 9: remove 'gene_abstract' links for abstracts not in 'abstract' table
    abstractqueries.remove_bad_links(db)

    # 10: populate 'homologene_gene_abstract' table
    abstractqueries.make_homolog_links(db)

    # 10: update abstract index - add new abstracts and "index_dirty" abstracts
    buildindex.update_index(db)

    # 11: update 'gene' table, count abstracts for each gene
    abstractqueries.count_genes(db)

    logger.info('Completed GADGET data update.')
