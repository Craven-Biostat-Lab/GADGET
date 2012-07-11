
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


def add_new_abstracts():
    """Add abstracts from the 'gene_abstract' link table to the 'abstract'
    table."""

    logger.debug('adding abstract id\'s from gene_abstract table to the abstract table')

    try:
        c.execute("""
        insert ignore into `abstract` (`pubmed_id`)
        select distinct `abstract` from `gene_abstract`; 
        """)
    except Exception as e:
        logger.critical('could not insert add new abstract ID\'s from gene-abstract links into abstract table.  Error message: %s', e)
        raise

    logger.info('added new abstract ID\'s to abstract table')


def remove_too_many_genes(maxgenes=1000):
    """Remove abstracts associated with more than 'maxgenes' (default 1000)
    genes to get rid of GWA papers"""

    logger.debug('removing abstracts from `abstract` table with too many (> %s) associated genes', maxgenes)

    try:
        c.execute("""

        """)
