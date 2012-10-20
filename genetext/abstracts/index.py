#!/usr/bin/python
import atexit
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, IDLIST, BOOLEAN, STORED
from whoosh.qparser import MultifieldParser
from whoosh.query import And, Term, ConstantScoreQuery, NullQuery, Query
from whoosh.scoring import BM25F
from whoosh.sorting import MultiFacet

from django.core.cache import cache

try:
    from genetext.settings import ABSTRACT_INDEX_PATH
except ImportError:
    ABSTRACT_INDEX_PATH = '/home/genetext/gadget/index'

# open or create the index
if index.exists_in(ABSTRACT_INDEX_PATH):
    ix = index.open_dir(ABSTRACT_INDEX_PATH)
else:
    # define the index fields
    class Schema(SchemaClass):
        pmid = NUMERIC(stored=True, unique=True, signed=False)
        genes = IDLIST(stored=True) # Entrez ID's
        homolog_genes = IDLIST(stored=True) # Entrez ID's
        title = TEXT(stored=True)
        abstract = TEXT
        authors = TEXT(stored=True)
        year = NUMERIC(stored=True)
        month = NUMERIC(stored=True)
        day = NUMERIC(stored=True)
        review = BOOLEAN(stored=True)
        journal = STORED
        volume = STORED
        pages = STORED
        
    ix = index.create_in(ABSTRACT_INDEX_PATH, Schema)

# query parser and searcher
parser = MultifieldParser(fieldnames=('title', 'abstract'), schema=ix.schema)
searcher = ix.searcher(weighting=BM25F)

# facet object for sorting abstracts by date (some have years but not dates)
datefacet = MultiFacet()
datefacet.add_field('year')
datefacet.add_field('month')
datefacet.add_field('day')

def cachekey(keywords='', genes=(), genehomologs=True):
    """Return a key to use for cached query results"""
    
    if genes is None:
        genes = ()
        
    if keywords is None:
        keywords=''
    
    return 'query_k:{0}_g:{1}_h:{2}'.format(
        keywords.replace(' ', '_'),
        hash(genes),
        genehomologs)


def buildquery(keywords=None, genes=None, genehomologs=True, onlyreviews=False, scored=False):
    """Return a whoosh query object for searching the index"""
    
    # decide which index field to use for genes, based upon whether we're
    # using homologs
    genefield = 'homolog_genes' if genehomologs else 'genes'
    
    # build gene branch of query.  If genes is a list, AND the entries together.
    if genes is not None:   
        if isinstance(genes, Query):
            genebranch = genes
        else:
            genebranch = And([Term(genefield, unicode(g)) for g in genes])
    else:
        genebranch = NullQuery()
        
    # get keyword branch of query
    keywordbranch = parser.parse(unicode(keywords)) if keywords else NullQuery()
    
    reviewbranch = Term('review', u't') if onlyreviews else NullQuery()

    # return query, don't score each abstract
    if scored:
        return genebranch & keywordbranch & reviewbranch
    else:
        return ConstantScoreQuery(genebranch & keywordbranch & reviewbranch)


def get_abstracts(keywords=None, genes=None, genehomologs=True):
    """Return a list of PMID's for abstracts matching a keyword/gene query, 
    optionally including homologs."""
    
    # return an empty list if we don't have a query or list of genes
    if keywords is None and genes is None:
        return []
    
    # check to see if we've done this search already
    # return the cached results if the query is in the cache
    key = cachekey(keywords, genes, genehomologs)
    cached = cache.get(key)
    if cached:
        return cached
    
    # parse the query
    query = buildquery(keywords, genes, genehomologs)
    
    # search the index
    results = [r['pmid'] for r in searcher.search(query, limit=None)]
    
    # remember the results for 10 * 60 seconds
    cache.set(key, results, 600)
    
    return results


def abstracts_page(keywords=None, genes=None, genehomologs=True, limit=None, offset=None, orderby='relevance', onlyreviews=False):
    """Return a page of abstracts (as a Whoosh result object) matching a keyword/gene
    query.  Optionally specify limit and offset, orderby, whether to include gene
    homologs and whether to include only reviews.
    
    This function does not cache results (as opposed to get_abstracts, which 
    uses the cache.
    
    Valid options for "orderby" are 'relevance', 'oldest', and 'newest'.  Other
    orderby values will not order the results.
    """
    
    # raise an error if orderby is invalid
    if orderby not in (None, 'relevance', 'oldest', 'newest'):
        raise ValueError
    
    # return an empty list if we don't have a query or list of genes
    if keywords is None and genes is None:
        return []
        
    # build a query, scored if we're sorting by relevance
    # (don't score abstracts unles we have to, because scoring abstracts is slow.)
    if orderby == 'relevance':
        query = buildquery(keywords, genes, genehomologs, onlyreviews, scored=True)
    else:
        query = buildquery(keywords, genes, genehomologs, onlyreviews, scored=False)
    
    # we have to apply the limit before the offset, so add the offset to
    # the limit so we still get back the correct number of abstracts
    if limit and offset:
        limit += offset

    # search the index and return abstracts.  
    # whoosh page numbers start at 1
    if orderby == 'oldest':
        return searcher.search(query, sortedby=datefacet, limit=limit)[offset:]
    elif orderby == 'newest':
        return searcher.search(query, sortedby=datefacet, reverse=True, limit=limit)[offset:]
    else:
        # ordered by relevance (or not ordered)
        return searcher.search(query, limit=limit)[offset:]


def corpus_size():
    """Return the number of abstracts in the corpus"""
    return ix.doc_count()


@atexit.register
def close(): # close the index when the module is unloaded
    ix.close()

if __name__ == '__main__':
    print 'Updating the index...'
    updateIndex()
