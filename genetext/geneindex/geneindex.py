#!/usr/bin/python

import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, ID
from whoosh.query import And, Or, CompoundQuery, Term, NullQuery
from whoosh.qparser import QueryParser, OrGroup, AndGroup

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
        entrezID = ID(unique=True, stored=True)
        tax = ID
        symbol = TEXT
        name = TEXT
        synonyms = TEXT
    ix = index.create_in(GENE_INDEX_PATH, Schema)


# search 'symbol' and 'entrezID' fields by default
# orParser uses an implicit OR between adjacent query terms ("foo bar" is "foo OR bar")
# andParser uses an implicit AND ("foo bar" is "foo AND bar")
orParser = QueryParser('symbol', schema=ix.schema, group=OrGroup)
andParser = QueryParser('symbol', schema=ix.schema, group=AndGroup)
searcher = ix.searcher()


def setfield_entrezID(q):
    """Sets the 'fieldname' of a query object to 'entrezID' and returns it"""
    q.fieldname = 'entrezID'
    return q
    
def setfield_synonyms(q):
    """Sets the 'fieldname' of a query object to 'synonyms' and returns it"""
    q.fieldname = 'synonyms'
    return q

def lookup(q, tax):
    """Look up entrezID's in the gene index that match the given whoosh query
    object.  Return a list of entrezID's that satisfy the query in no particular 
    order.  Raise a LookupError if the query does not match any genes."""

    # add entrezID and synonyms fields to query (do this instead of using a
    # multifield parser so we can detect when a token didn't match any genes)
    query = Or((q, q.copy().accept(setfield_entrezID), q.copy().accept(setfield_synonyms)))
    
    # add the taxon constraint to the query
    if tax:
        query = And([query, Term('tax', str(tax))])

    genes = [g['entrezID'] for g in searcher.search(query, limit=None)]
    if genes:
        return genes
    else:
        print query
        raise LookupError()


def convert_to_abstractquery(query, tax=None, genefield='genes'):
    """Convert a gene query to a query to be used on the abstract index.
    Takes an already-parsed query obect (for genes), and recursively 
    re-builds the query into a query for the abstract index, where all of the
    leaf nodes are expanded into a set of entrezID's.  Throws a LookupError
    if there is a query term that doesn't match any genes."""

    if query == NullQuery:
        return query

    elif query.is_leaf():
        # if this node is a leaf, get the matching genes from the index, and
        # 'Or' them all together
        
        # return the genes matched by the leaf, all OR'd together.
        try:
            # lookup will raise a LookupError if the query does not match any genes
            return Or([Term(genefield, str(g)) for g in lookup(query, tax)])

        # if we get a LookupError, try to determine the bad text that caused it.
        except LookupError:
            # try to get the text of the bad query term, and attach it to the error
            try:
                raise LookupError(query.text)
            except AttributeError:
                # no query.text, try query.words instead
                try:
                    raise LookupError(u'"' + u' '.join(query.words) + u'"')
                except AttributeError:
                    # no query.text or query.words
                    raise LookupError()


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


def parse_abstractquery(q, tax=None, implicitOr=False, usehomologs=False):
    """Take a gene query as a string, and parse and convert it into a Whoosh 
    query object to be used against the abstract index.  Raise a LookupError 
    if there is a term in the query that doesn't match any genes."""
    
    # decide which gene field to use on the abstract index
    genefield = 'homolog_genes' if usehomologs else 'genes'

    genequery = parsequery(unicode(q), implicitOr)
    return convert_to_abstractquery(genequery, tax, genefield).normalize()
    

def flatten_query(query):
    """Given a query produced by parse_abstractquery, return a set of the text
    of all of the terms in the query (a set of all of the gene ID's as unicode
    strings.)"""

    # if this is the null query, return the empty set
    if query is None or query == NullQuery:
        return set()
    
    # if this query is a single term, return a set containing the text of the term    
    if isinstance(query, Term):
        return set([query.text])
    
    # otherwise, return the union of the terms of the query's children    
    else:
        union = set()
        for c in query.children():
            union.update(flatten_query(c))
        return union
