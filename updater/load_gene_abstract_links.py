#!/usr/bin/python
"""Fetch files with gene-abstract links from gene2pubmed, MGI, and SGD,
and load the files into the "gene_abstract" database table."""

import urllib
from os.path import join
import gzip

# set up logger
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler('gene2abstract.log'))

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

# TODO: get this from a config file later
datapath = '/home/genetext/update_data/gene_abstract_links'


class linksource:
    def __init__(self, url, filename, insertquery=None, insertfunction=None, compressiontype=None, compressedfilename=None):

        self.url = url
        self.filename = filename
        self.insertquery = insertquery
        self.insertfunction = insertfunction
        self.compressiontype = compressiontype
        self.compressedfilename = compressedfilename

        if not (insertquery or insertfunction):
            errmsg = 'Data source configuration error: you must provide either an insertquery or an insertfunction'
            logger.critical(errmsg)
            raise ValueError(errmsg)

        if compressiontype:
            if compressiontype not in ('gzip'):
                errmsg = 'Data source configuration error: unknown compressiontype "{ct}".  You might have to edit "load_g-a_links.py" to add support for a new type of compression.'.format(compressiontype)
                logger.critical(errmsg)
                raise ValueError(errmsg)

            if compressiontype and not compressedfilename:
                errmsg = 'Data source configuration error: if you provide a compression type, you must also provide a compressedfilename'
                logger.critical(errmsg)
                raise ValueError(errmsg)
    

def fetch(source):
    """Fetch and decompress the specified url into the filename, use logging.
    Return True if the retrieval was successful, False otherwise."""

    try:
        # use filename if the file is not compressed
        name = source.compressedfilename or source.filename

        logger.debug('retrieving gene-abstract links from "%s", saving file as "%s"', source.url, name)
        urllib.urlretrieve(source.url, join(datapath, name))

    except IOError as e:
        logger.error('could not retrieve a file, maybe the network connection is bad or the file moved.  file :"%s"   error :%s', source.url, e)
        return False
    else:
        logger.info('retrieved gene-abstract links from "%s", saving file as "%s"', source.url, name)
        return decompress(source)


def decompress(source):
    """Decompress a file according to its 'decompressiontype', and save the 
    decompressed file as the source's filename.  If the file is not compressed,
    do nothing.  Return true if successful."""

    if source.compressiontype == 'gzip':
        logger.debug('decompressing file %s', source.compressedfilename)

        try:
            f_in = gzip.open(join(datapath, source.compressedfilename), 'rb')
            f_out = open(join(datapath, source.filename), 'wb')

            f_out.writelines(f_in)
           
            f_in.close()
            f_out.close()

        except IOError as e:
            logger.error('IOError decompressing file %s, the file might not exist or might not be a gzipped file.  error message: %s', 
                source.compressedfilename, e)
            return False

        except gzip.zlib.error as e:
            logger.error('zlib error while decompressing file %s, the file might be corrupt.  error message: %s',
                source.compressedfilename, e)
            return False

        else:
            return True

    # return true if this is not a compressed file
    logger.info('decompressed file %s', source.compressedfilename)
    return True


def insert(source):
    """Insert a source into the database"""

    logger.debug('Inserting %s into gene_abstract database table', source.filename)

    # check to see if this source has a function for insertion
    if source.insertfunction:
        return source.insertfunction(source)

    # otherwise insert by executing its 'insertquery'
    try:
        c.execute(source.insertquery.format(path=join(datapath, source.filename)))
    except Exception as e:
        logger.error('error inserting %s into gene_abstract database table.  Maybe the format of the file changed?  Error message: %s', source.filename, e)
        return False
    else:
        logger.info('Inserted %s into gene_abstract database table', source.filename)
        return True


def insertMGI(source):
    """Load the MGI 'MRK_Reference.rpt' file into the gene_abstract table.
    Return true if successful."""
    
    # on each line, the MGI file has an MGI marker ID and a list of PMID's
    # separated by |'s

    logger.debug('Inserting MGI links into table using insertMGI function')

    # We need to insert the gene-abstract links one-by-one because we have more
    # than one link per row in the file.
    # Put them into a separate table first and then get gene Entrez ID's with
    # a join, because it would be very slow to look them up with a subquery.
    query = \
    """insert ignore into `mgi_reference` (`mgi_marker`, `abstract_pmid`) values {values}"""

    try:
        f = open(join(datapath, source.filename))
        for line in f:
            fields = line.split('\t')
            MGI_marker = fields[0]
            PMIDs = fields[-1].split('|')

            c.execute(query.format(values=','.join(['(%s, %s)' for p in PMIDs])),  
                [val for p in PMIDs for val in (MGI_marker, p)])    
    except Exception as e:
        logger.error('Error inserting MGI gene-abstract links into `mgi_reference` table.  Maybe the format of the file changed?  Error message: %s', e)
        return False

    # insert links into gene_abstract table
    try:
        c.execute("""insert ignore into `gene_abstract`
        select null `id`, e.`entrez_id` `gene`, r.`abstract_pmid` `abstract_pmid`
        from `mgi_reference` r
        inner join `mgi_entrez_gene` e
        using (`mgi_marker`);""")
    except Exception as e:
        logger.error('Error inserting MGI gene-abstract links into `gene_abstract` table (from `mgi_reference` table.)  Error message: %s', e)
        return False

    # no exceptions
    logger.info('Inserted MGI links into table using insertMGI function')
    return True


def load(source):
    """Fetch / decompress a gene-abstract link source and insert it into the 
    database.  Return true if successful."""

    if fetch(source):
        return insert(source)
    else:
        return False


def loadall():
    """Fetch, decompress, and insert all sources in the 'sources' list into 
    the database.  Return true if all loads were successful."""
    
    return not (False in [load(source) for source in sources])


def cleanup():
    """Remove gene-abstract links with gene or abstract IDs set to 0."""

    logger.debug('Removing gene_abstracts with gene or abstract ID set to 0')

    try:
        c.execute("""
        delete from `gene_abstract`
        where `abstract_pmid` = 0
        or `gene` = 0;
        """)
    except Exception as e:
        logger.error('Error removing bad gene_abstract links, error message: %s', e)
    
    logger.info('Removed gene_abstracts with gene or abstract ID set to 0')


# TODO: get these from config file
sources = [    
    # gene2pubmed
    linksource(
        url = 'ftp://ftp.ncbi.nih.gov/gene/DATA/gene2pubmed.gz',
        filename = 'gene2pubmed',
        compressiontype = 'gzip',
        compressedfilename = 'gene2pubmed.gz',
        insertquery = \
            """load data local infile '{path}'
            into table `gene_abstract`
            fields terminated by '\t'
            ignore 1 lines
            (@tax_id, `gene`, `abstract_pmid`);"""
    ),
    
    # SGD
    # requires "sgd_xrefs" table
    linksource(
        url = 'http://downloads.yeastgenome.org/curation/literature/gene_literature.tab',
        filename = 'SGD_gene_literature.tab',
        insertquery = \
            """load data local infile '{path}'
            into table `gene_abstract`
            fields terminated by '\t'
            (`abstract_pmid`, @citation, @genename, @feature, @topic, @sgd_gene_id)
            set `gene` = (select `xref_id` from `sgd_xrefs` where `sgd_gene_id` = @sgd_gene_id limit 1);"""
    ),

    # MGI
    # requires mgi_entrez_gene (must be populated) 
    # and mgi_reference (can be enpty) tables
    linksource(
        url = 'ftp://ftp.informatics.jax.org/pub/reports/MRK_Reference.rpt',
        filename = 'MGI_MRK_Reference.rpt',
        insertfunction = insertMGI,
        ),
    ]


if __name__ == '__mai__':
    print "Loading all sources" 
    print "Successful: ", loadall()
    print "Cleaning up..."
    cleanup()

if __name__ == '__main__':
    insert(sources[0])
    insert(sources[1])
    insert(sources[2])
