#!/usr/bin/python

import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC
from whoosh.query import Or, CompoundQuery, Term

# Get index location out of the config file
# If we can't, use a hard-coded path
try:
    from genetext.settings import GENE_INDEX_PATH
except ImportError:
    GENE_INDEX_PATH = '/home/genetext/gadget/gene-index'

searcher = ix.searcher()

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


def lookup(query):
    """Look up entrezID's in the gene index that match the given whoosh query
    object.  Return a list of entrezID's that satisfy the query in no particular 
    order."""

    return [g['entrezID'] for g in searcher.search(query, limit=None)]


def convert_to_abstractquery(query, genefield='genes'):
    """Convert a gene query to a query to be used on the abstract index.
    Takes an already-parsed query obect (for genes), and recursively 
    re-builds the query into a query for the abstract index, where all of the
    leaf nodes are expanded into a set of entrezID's."""

    if query.is_leaf():
        # if this node is a leaf, get the matching genes from the index, and
        # 'Or' them all together.
        return Or([Term(genefield, g) for g in lookup(query)])

    elif isinstance(query, CompoundQuery):
        # this node has a list of children
        # recursively convert each of thid node's children to abstract queries
        children = [convert_to_abstractquery(c) for c in query.all_children()]

        # return this node with new children
        return query.__class__(children)

    else:
       # this node only has one child
       child = list(query.children())[0]

       # recursively convert this node's children to an abstract query, and
       # return it
       return query.__class__(convert_to_abstractquery(child))
