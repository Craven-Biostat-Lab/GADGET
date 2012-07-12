#!/usr/bin/python

# set up logging
import logging
logger = logging.getLogger(__name__)

# TODO: get this from a configuration file
dbparams = {'user': 'root', 'passwd': 'password', 'db': 'updater'}

# set up database connection
try:
    import MySQLdb
    db = MySQLdb.connect(**dbparams)
    c = db.cursor()

    # unicode stuff
    db.set_character_set('utf8')
    c.execute('SET NAMES utf8;')
    c.execute('SET CHARACTER SET utf8;')
    c.execute('SET character_set_connection=utf8;')
except Exception as e:
    logger.critical('Error connecting to database.  Error message: %s', e)
    raise

def add_new_abstracts():
    """Add abstracts from the 'gene_abstract' link table to the 'abstract'
    table."""

    logger.debug('adding abstract id\'s from gene_abstract table to the abstract table')

    try:
        c.execute("""
        insert ignore into `abstract` (`pubmed_id`)
        select distinct `abstract_pmid` from `gene_abstract`; 
        """)
    except Exception as e:
        logger.critical('Error inserting add new abstract ID\'s from gene-abstract links into abstract table.  Error message: %s', e)
        raise

    logger.info('added new abstract ID\'s to abstract table')


def find_too_many_genes(maxgenes=1000):
    """Find abstracts with more than 'maxgenes' (1000 by default) associated 
    genes, and then add them to the 'removed_abstracts' table to get rid of 
    GWA papers"""

    logger.debug('adding abstracts to `removed_abstracts` table with too many (> %s) associated genes', maxgenes)

    try:
        c.execute("""
        insert ignore into `removed_abstracts`
        (`abstract_pmid`, `removed`, `reason`)
        select `abstract_pmid`, now() `removed`, 1 `reason`
        from `gene_abstract`
        group by `abstract_pmid`
        having count(`gene`) > %s
        """, (maxgenes,))
    except Exception as e:
        logger.critical('Error adding abstracts with too many genes (> %s) to `removed_abstracts` table.  Error message: %s', maxgenes, e)
        raise

    logger.info('added abstracts to `removed_abstracts` table with too many (> %s) associated genes', maxgenes)


def remove_bad_abstracts():
    """Remove abstracts in the 'removed_abstracts' table from the 'abstract' table"""

    logger.debug('removing abstracts in the `removed_abstracts` table from the `abstract` table')

    try:
        c.execute("""
        delete `abstract`
        from `abstract`
        inner join `removed_abstracts`
        on `abstract`.`pubmed_id` = `removed_abstracts`.`abstract_pmid`
        """)
    except Exception as e:
        logger.critical('Error removing abstracts in the `removed_abstracts` table from the `abstract` table.  Error message: %s', e)
        raise

    logger.info('removed abstracts in the `removed_abstracts` table from the `abstract` table')
