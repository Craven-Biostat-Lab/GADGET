#!/usr/bin/python
"""
Queries the Whoosh index of abstracts.  This module is used by all of the search
modes to execute the queries, to find all of the relevant abstracts before
ranking genes/metabolites/keyphrases/events.  It's also used by abstracts/abstracts.py,
for getting lists of abstracts to show to the user.
"""


import atexit
import whoosh.index as index
from whoosh.fields import SchemaClass, TEXT, NUMERIC, IDLIST, BOOLEAN, STORED
from whoosh.qparser import MultifieldParser
from whoosh.query import And, Or, Term, ConstantScoreQuery, NullQuery, Query
from whoosh.scoring import BM25F
from whoosh.sorting import MultiFacet
#from whoosh.legacy import int_to_text
from whoosh.codec.whoosh2 import int_to_text


from django.core.cache import cache

from django.conf import settings 

# open or create the index
if index.exists_in(settings.ABSTRACT_INDEX_PATH):
    ix = index.open_dir(settings.ABSTRACT_INDEX_PATH)
else:
    # define the index fields
    class Schema(SchemaClass):
        pmid = NUMERIC(stored=True, unique=True, signed=False)
        genes = IDLIST(stored=True) # Entrez ID's
        homolog_genes = IDLIST(stored=True) # Entrez ID's
        metabolites = IDLIST(stored=True) # HMDB ID's
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
        
    ix = index.create_in(settings.ABSTRACT_INDEX_PATH, Schema)

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


def buildquery(keywords=None, genes=None, genehomologs=True, onlyreviews=False, scored=False, abstractlist=None, metabolite=None):
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
    if keywords is not None:
	keywords = keywords.replace(":[to",":{0 to")
    keywordbranch = parser.parse(unicode(keywords)) if keywords else NullQuery()
    
    # include only reviews?
    reviewbranch = Term('review', u't') if onlyreviews else NullQuery()
    
    # restrict to a certain set of abstracts?
    if abstractlist:
        abstractbranch = Or([Term('pmid', int_to_text(a, signed=False)) for a in abstractlist])
    else:
        abstractbranch = NullQuery()
        
        
    # metabolite ID
    if metabolite:
        metabolitebranch = Term('metabolites', unicode(metabolite))
    else:
        metabolitebranch = NullQuery()
        


    # return query, don't score each abstract
    if scored:
        return genebranch & keywordbranch & reviewbranch & abstractbranch & metabolitebranch
    else:
        return ConstantScoreQuery(genebranch & keywordbranch & reviewbranch & abstractbranch & metabolitebranch)


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


def abstracts_page(keywords=None, genes=None, genehomologs=True, limit=None, offset=None, orderby='relevance', onlyreviews=False, abstractlist=None, metabolite=None):
    """Return a page of abstracts (as a Whoosh result object) matching a keyword/gene
    query.  Optionally specify limit and offset, orderby, whether to include gene
    homologs and whether to include only reviews.
    
    This function does not cache results (as opposed to get_abstracts, which 
    uses the cache.
    
    Valid options for "orderby" are 'relevance', 'oldest', and 'newest'.  Other
    orderby values will not order the results.
    
    If given an "abstractlist" option (as a list of pubmed ID's), this function 
    will return only abstracts in that list.
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
        query = buildquery(keywords, genes, genehomologs, onlyreviews, True, abstractlist, metabolite)
    else:
        query = buildquery(keywords, genes, genehomologs, onlyreviews, False, abstractlist, metabolite)
    
    # we have to apply the limit before the offset, so add the offset to
    # the limit so we still get back the correct number of abstracts
    if limit and offset:
        limit += offset

    #print query

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
