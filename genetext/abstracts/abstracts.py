#!/usr/bin/python
"""
Django views for showing lists of abstracts in all of the search modes.

The view functions in this file interact with abstracts/index.py, which has code
for accessing the Whoosh full-text index of abstracts.
"""


import json
from whoosh.query import NullQuery

from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from django.shortcuts import render_to_response

from geneview.geneview import parseboolean
from index import abstracts_page
from geneindex.geneindex import parse_gene_abstractquery, gene_id_list, genefile_lookup, BadGenefileError, addgene
from models import Abstract, KeyPhrase, KeyphraseAbstract, Gene, Metabolite

def abstracts(request):
    """Return a list of abstracts (as HTML wrapped in JSON) for a keyword
    query and list of genes."""

    # get species, default=human
    try:
        species = int(request.GET['species'])
    except (KeyError, ValueError):
        species = 9606
    
    # get gene operator (any (or) / all (and))
    try:
        geneop = request.GET['geneop'].lower()
        if geneop == 'all':
            implicitOr = False
        else:
            geneop = 'any'
            implicitOr = True
    except KeyError:
        geneop = 'any'
        implicitOr = True

    # figure out if we should include homologs
    try:
        usehomologs = parseboolean(request.GET['usehomologs'])
    except (KeyError, ValueError):
        usehomologs = False  
        
    # get keyword arguments from query string
    keywords = request.GET.get('q')

    # get genes from query string
    try:
        if parseboolean(request.GET.get('usegenefile')):
            # look up genes from file if we're using one
            genefileID = request.GET.get('genefileID', -1)
            genes = genefile_lookup(genefileID, implicitOr, usehomologs)
        elif request.GET.get('genes'):
            gene_query = request.GET.get('genes')
            genes = parse_gene_abstractquery(gene_query, species, implicitOr, usehomologs)
        else:
            genes = NullQuery

        if request.GET.get('rowgene'):
            genes = addgene(genes, request.GET.get('rowgene'), species, usehomologs)

        # apply gene filter
        if request.GET.get('genefilter'):
            genes = addgene(genes, request.GET.get('genefilter'), species, usehomologs)

    except LookupError as e:
        # bad gene query
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'Bad gene query.  Check your gene symbols: {0}.'.format(e.args[0])}, response)
        return response
    except BadGenefileError:
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': "Can't find this gene file!  It probably expired.  Please upload it again."})
        return response

    # should we only include reviews?
    try:
        onlyreviews = parseboolean(request.GET['onlyreviews'])
    except (KeyError, ValueError):
        onlyreviews = False
    
    # error if no query
    if not keywords and not genes:
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'You must supply either genes or a query'}, response)
        return response
    
    # get sorting parameter
    orderby = request.GET.get('orderby')
    if orderby: orderby = orderby.lower()
    if orderby not in (None, 'relevance', 'oldest', 'newest'):
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'Invalid "orderby."  Valid options are None, "relevance", "oldest", or "newest".'}, response)
        return response
    
    # get limit and offset
    try: offset = int(request.GET.get('offset'))
    except: offset = 0
    try: limit = int(request.GET.get('limit'))
    except: limit = None
    
    # get keyword ID from query string
    keywordID = request.GET.get('keywordnum')
    if keywordID:
        keyword_abstracts = [a.pubmed_id for a in Abstract.objects.filter(ka_abstract__keyphrase=keywordID).only('pubmed_id')]
    else:
        keyword_abstracts = None
        
        
    # get optional metabolite ID
    metabolite = request.GET.get('metabolite')
    
    
    # get abstract ID's from index
    abstracts = abstracts_page(keywords, genes, usehomologs, limit, offset, orderby, onlyreviews, keyword_abstracts, metabolite)
    
    # error if no abstracts
    if not abstracts:
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'No more abstracts!'}, response)
        return response
    
    # create response
    resulthtml = render_to_string('abstracts.html', {'abstracts': abstracts})
    response = HttpResponse()
    json.dump({'validresult': True, 'result': resulthtml}, response)
    return response


def filter_genes(genelist, keywordnum=None, geneID=None):
    """Given a list of gene ID's and a keyword ID, return a list of gene symbols
    from the genes in the list that are related to the keyword in the database"""
    
    genes = Gene.objects.only('symbol').distinct().filter(entrez_id__in=genelist)
    
    if keywordnum:
      genes = genes.filter(geneabstract__abstract__ka_abstract__keyphrase=keywordnum)
  
    return [g.symbol for g in genes]
  


def lookup_metabolitename(HMDBID):
    """
    Given an HMDB ID, look up the name to display to the user.
    """
    
    return Metabolite.objects.get(hmdb_id=HMDBID).common_name
    



def abstractview(request):
    """Render the container page for displaying abstracts"""
    q = request.GET.get('q')
    species = request.GET.get('species')
    genes = request.GET.get('genes')
    genesyms = request.GET.get('genesyms')
    geneop = request.GET.get('geneop')
    usehomologs = request.GET.get('usehomologs')
    onlyreviews = request.GET.get('onlyreviews')
    orderby = request.GET.get('orderby')
    offset = request.GET.get('offset')
    unique = request.GET.get('unique')
    abstractcount = request.GET.get('abstractcount')
    rowgene = request.GET.get('rowgene')
    keywordnum = request.GET.get('keywordnum')
    genefilter = request.GET.get('genefilter')
    usegenefile = request.GET.get('usegenefile')
    genefileID = request.GET.get('genefileID')
    metabolite = request.GET.get('metabolite')


    # clean up gene symbols
    if genesyms:
        genesyms = ', '.join(set([s.strip() for s in genesyms.split(',') if s]))

    if orderby:
        orderby = orderby.lower()
    
    # turn onlyreviews into a boolean
    if onlyreviews:
        onlyreviews = parseboolean(onlyreviews)
        
    if usegenefile:
        usegenefile = parseboolean(usegenefile)

    # look up keyword string
    if keywordnum:
        keywordstring = KeyPhrase.objects.get(pk=keywordnum).string
    else:
        keywordstring = None

    # get gene list (from gene query)
    # only if this is a keyword search (for now)
    if keywordnum and genes:
        gene_symbol_list = filter_genes(gene_id_list(genes, species), keywordnum=keywordnum)
        
        if genefilter not in gene_symbol_list:
            genefilter = None # show gene filter option, but with none selected
    else:
        genefilter = None
        gene_symbol_list = []
        
        
    # look up metabolite
    if metabolite:
        metabolite_name = lookup_metabolitename(metabolite)
    else:
        metabolite_name = None
        

    return render_to_response('abstractview.html', {'q':q,
        'species':species, 'genes':genes, 'genesyms': genesyms, 'geneop': geneop,
        'usehomologs':usehomologs, 'onlyreviews':onlyreviews, 
        'orderby':orderby, 'offset':offset,
        'unique':unique, 'abstractcount':abstractcount, 'rowgene':rowgene,
        'keywordnum': keywordnum, 'keywordstring': keywordstring,
        'gene_symbol_list': gene_symbol_list, 
        'usegenefile': usegenefile, 'genefileID': genefileID,
        'metabolite_id': metabolite, 'metabolite_name': metabolite_name
        })
        
