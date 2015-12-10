#!/usr/bin/python
"""
Config file for GADGET automatic data updates
"""


# connection string for database
dbparams = {'user': 'root', 'db': 'gadget'}



import os
BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# path and filename for log files.
# log files rotate, so old log files are kept and suffixed with numbers.
logfilename = os.path.join(BASE_DIR, '../../gadget-data/updater-workspace/updater.log')

# minimum severity of events to record in log.
# valid options are 'DEBUG', 'INFO', 'WARNING', 'ERROR', and 'CRITICAL'.
# see http://docs.python.org/howto/logging.html for log level descriptions.
loglevel = 'DEBUG'



# path to abstract Whoosh index to update
ABSTRACT_INDEX_PATH = os.path.join(BASE_DIR, '../../gadget-data/abstracts')



# directory to store downloaded files
# (nothing needs to be in here when the script runs, but the script will not
# delete the files that it downloads.  It will write over the files every time
# the script runs.)
datapath = os.path.join(BASE_DIR, '../../gadget-data/updater-workspace')

# url for fetching abstracts from PubMed
# the script will format this with a comma-separated list of PubMed ID's
abstracturl = """http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={0}&rettype=abstract&retmode=xml"""

# number of abstracts to fetch at a time from PubMed
abstract_fetch_batchsize = 200

# function for creating database cursors.  Make sure this is set up to 
# properly handle unicode over your database connection.
def getcursor(db):
    """Create and return a cursor from the database connection"""
    
    try:
        c = db.cursor()
        c.execute('SET NAMES utf8;')
        c.execute('SET CHARACTER SET utf8;')
        c.execute('SET character_set_connection=utf8;')
    except Exception as e:
        logger.critical('Error creating database cursor.  Error message: %s', e)
        raise

    return c

# sources from which to download gene-abstract links
# The scipt will download the file from the given url, and save it as the
# given filename in the data directory.  If the file is compressed,
# provide a 'compressiontype', and a 'compressedfilename' that is different
# from the filename.  The 'insertfunction' will be called by the script after
# the file has been downloaded and decompressed to insert the file contents
# into the database.  If no 'insertfunction' is given, the script will execute
# the SQL 'insertquery', formatted with the path to the file.

#from load_gene_abstract_links import linksource, insertMGI
import load_gene_abstract_links as ga
ga_sources = [    
    # gene2pubmed
    ga.linksource(
        url = 'ftp://ftp.ncbi.nih.gov/gene/DATA/gene2pubmed.gz',
        filename = 'gene2pubmed',
        compressiontype = 'gzip',
        compressedfilename = 'gene2pubmed.gz',
        insertquery = \
            """load data local infile '{path}'
            into table `gene_abstract`
            fields terminated by '\t'
            ignore 1 lines
            (@tax_id, `gene`, `abstract`);"""
    ),
    
    # SGD
    # requires "sgd_xrefs" table
    ga.linksource(
        url = 'http://downloads.yeastgenome.org/curation/literature/gene_literature.tab',
        filename = 'SGD_gene_literature.tab',
        insertquery = \
            """load data local infile '{path}'
            into table `gene_abstract`
            fields terminated by '\t'
            (`abstract`, @citation, @genename, @feature, @topic, @sgd_gene_id)
            set `gene` = (select `xref_id` from `sgd_xrefs` where `sgd_gene_id` = @sgd_gene_id limit 1);"""
    ),

    # MGI
    # requires mgi_entrez_gene (must be populated) 
    # and mgi_reference (can be enpty) tables
    ga.linksource(
        url = 'ftp://ftp.informatics.jax.org/pub/reports/MRK_Reference.rpt',
        filename = 'MGI_MRK_Reference.rpt',
        insertfunction = ga.insertMGI,
    ),
    ]
