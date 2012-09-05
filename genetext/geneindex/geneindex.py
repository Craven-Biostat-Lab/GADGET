#!/usr/bin/python

import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, ID
from whoosh.query import And, Or, CompoundQuery, Term
from whoosh.qparser import MultifieldParser, OrGroup, AndGroup

# Get index location out of the config file
# If we can't, use a hard-coded path
try:
    from genetext.settings import GENE_INDEX_PATH
except ImportError:
    GENE_INDEX_PATH = '/home/genetext/gadget/gene-index'


# open gene index
if index.exists_in(GENE_INDEX_PATH):
    ix = index.open_dir(GENE_INDEX_PATH)
else:
    # define gene index fields
    class Schema(SchemaClass):
        entrezID = NUMERIC(unique=True, signed=False, stored=True)
        tax = ID
        symbol = TEXT
        name = TEXT
        synonyms = TEXT
    ix = index.create_in(GENE_INDEX_PATH, Schema)


# search 'symbol' and 'entrezID' fields by default
# orParser uses an implicit OR between adjacent query terms ("foo bar" is "foo OR bar")
# andParser uses an implicit AND ("foo bar" is "foo AND bar")
orParser = MultifieldParser(fieldnames=('symbol', 'entrezID'), schema=ix.schema, group=OrGroup)
andParser = MultifieldParser(fieldnames=('symbol', 'entrezID'), schema=ix.schema, group=AndGroup)
searcher = ix.searcher()


def lookup(query):
    """Look up entrezID's in the gene index that match the given whoosh query
    object.  Return a list of entrezID's that satisfy the query in no particular 
    order."""

    return [g['entrezID'] for g in searcher.search(query, limit=None)]


def convert_to_abstractquery(query, tax=None, genefield='genes'):
    """Convert a gene query to a query to be used on the abstract index.
    Takes an already-parsed query obect (for genes), and recursively 
    re-builds the query into a query for the abstract index, where all of the
    leaf nodes are expanded into a set of entrezID's."""

    if query.is_leaf():
        # if this node is a leaf, get the matching genes from the index, and
        # 'Or' them all together.
        
        # add the taxon constraint to the query
        if tax:
            query = And([query, Term('tax', str(tax))])
        
        return Or([Term(genefield, g) for g in lookup(query)])

    elif isinstance(query, CompoundQuery):
        # this node has a list of children
        # recursively convert each of thid node's children to abstract queries
        children = [convert_to_abstractquery(c, tax, genefield) for c in query.children()]

        # return this node with new children
        return query.__class__(children)

    else:
       # this node only has one child
       child = list(query.children())[0]

       # recursively convert this node's children to an abstract query, and
       # return it
       return query.__class__(convert_to_abstractquery(child, tax, genefield))


def parsequery(q, implicitOr=False):
    """Take a query as a unicode string, and parse it into a Whoosh query
    object against the gene index.  Use an implicit OR between adjacent query
    terms (eg. "foo bar" is "foo OR bar" if implicitOr is True, use an implicit
    AND otherwise ("foo bar" is "foo AND bar")."""

    if implicitOr:
        return orParser.parse(q)
    else:
        # implicit AND
        return andParser.parse(q)


def parse_abstractquery(q, tax=None, implicitOr=False, genefield='genes'):
    """Take a gene query as a string, and parse and convert it into
    a Whoosh query object to be used against the abstract index."""
    
    genequery = parsequery(unicode(q), implicitOr)
    return convert_to_abstractquery(genequery, tax, genefield).normalize()
