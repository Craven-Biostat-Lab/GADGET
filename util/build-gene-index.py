#!/usr/bin/python

import MySQLdb
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, ID

GENE_INDEX_PATH = '/home/genetext/gadget/index/genes'

# open gene index
if index.exists_in(GENE_INDEX_PATH):
    ix = index.open_dir(GENE_INDEX_PATH)
else:
    # define gene index fields
    class Schema(SchemaClass):
        entrezID = ID(unique=True, stored=True)
        tax = ID
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


def synonyms_dict(db):
    """Return a set of (symbol, taxon) tuples, and a dict of (synonym, taxon) 
    tuples and associated gene counts in the genes table for weeding out ambiguous 
    synonyms"""

    symbols = set()
    synonyms = dict() # (synonym, taxon) tuple is key, gene count is value
    
    for g in getgenes(db):
        tax = g[1]
        
        symbols.add((g[2].lower(), tax))
        
        for syn in g[4].split(','):
            syn = syn.strip().lower()
            
            if (syn, tax) in synonyms:
                synonyms[syn, tax] += 1
            else:
                synonyms[syn, tax] = 1
                
    return symbols, synonyms


def ambiguous(syn, tax, symbols, synonyms):
    """Return true if a symbol is ambiguous (if it is a symbol or a synonym for
    another gene for the same taxon."""
    
    s = syn.strip().lower()
    return ((s,tax) in symbols) or (synonyms[s, tax] > 1)


def write(genes, ix, all_symbols, all_synonyms):
    """Write and commit the supplied genes to the index."""

    writer = ix.writer()

    for g in genes:
        entrezID, tax, symbol, name, synonyms = g

        # remove ambiguous synonyms
        if synonyms is not None:
            synonyms = ' '.join([s.strip() for s in synonyms.split(',') 
                if not ambiguous(s, tax, all_symbols, all_synonyms)])

        # make all text fields unicode
        if entrezID is not None:
            entrezID = unicode(str(entrezID), 'utf-8')
        if tax is not None:
            tax = unicode(str(tax), 'utf-8')
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
    symbols, synonyms = synonyms_dict(db)
    write(genes, ix, symbols, synonyms)
