#!/usr/bin/python

import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, IDLIST

GENE_INDEX_PATH = '/home/genetext/gadget/gene-index'

# open gene index
if index.exists_in(GENE_INDEX_PATH):
    ix = index.open_dir(GENE_INDEX_PATH)
else:
    # define gene index fields
    class Schema(SchemaClass):
        geneID = NUMERIC(unique=True, signed=False)
        tax = NUMERIC
        symbol = TEXT
        name = TEXT
        synonyms = TEXT
        homologene_group: IDLIST
    ix = index.create_in(GENE_INDEX_PATH, Schema)

def getgenes(db):
    """Fetch rows from the `genes` table to insert into the index,
    return an iterator over rows"""
    
    c = get_cursor(db)

    c.execute("""
    select `entrez_id`, `tax_id`, `symbol`, `name`, `synonyms`
    from `gene`
    """)

    for gene in c:
        yield gene

    c.close()
