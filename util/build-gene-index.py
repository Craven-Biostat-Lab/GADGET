#!/usr/bin/python

import MySQLdb
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC

GENE_INDEX_PATH = '/home/genetext/gadget/gene-index'

# open gene index
if index.exists_in(GENE_INDEX_PATH):
    ix = index.open_dir(GENE_INDEX_PATH)
else:
    # define gene index fields
    class Schema(SchemaClass):
        entrezID = NUMERIC(unique=True, signed=False, stored=True)
        tax = NUMERIC
        symbol = TEXT
        name = TEXT
        synonyms = TEXT
    ix = index.create_in(GENE_INDEX_PATH, Schema)


# set up database connection
import MySQLdb
dbparams = {'user': 'root', 'passwd': 'password', 'db': 'production'}
db = MySQLdb.connect(**dbparams)
db.set_character_set('utf8')

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


def getgenes(db):
    """Fetch rows from the `genes` table to insert into the index,
    return an iterator over rows"""
    
    c = getcursor(db)

    c.execute("""
    select `entrez_id`, `tax_id`, `symbol`, `name`, `synonyms`
    from `gene`
    """)

    for gene in c:
        yield gene

    c.close()


def write(genes, ix):
    """Write and commit the supplied genes to the index."""

    writer = ix.writer()

    for g in genes:
        entrezID, tax, symbol, name, synonyms = g

        # make all text fields unicode
        if symbol is not None:
            symbol = unicode(symbol, 'utf-8')
        if name is not None:
            name = unicode(name, 'utf-8')
        if synonyms is not None:
            synonyms = unicode(synonyms, 'utf-8')
        
        # write the gene to the index
        writer.update_document(entrezID=entrezID, tax=tax, symbol=symbol, name=name, synonyms=synonyms)

    # commit the index
    writer.commit(optimize=True)


if __name__ == '__main__':
    genes = getgenes(db)
    write(genes, ix)
