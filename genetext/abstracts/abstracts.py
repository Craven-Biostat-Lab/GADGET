#!/usr/bin/python
import json

from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from django.shortcuts import render_to_response

from genetext.geneview.geneview import  parseboolean
from genetext.abstracts.index import abstracts_page
from genetext.geneindex.geneindex import parse_abstractquery, gene_id_list
from genetext.abstracts.models import Abstract, KeyPhrase, KeyphraseAbstract, Gene

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
        gene_query = request.GET.get('genes', '')
        
        # apply gene filter
        if request.GET.get('genefilter'):
          gene_query = request.GET['genefilter'] + ' AND ( ' + gene_query + ' )'
        
        genes = parse_abstractquery(gene_query, species, implicitOr, usehomologs)
    except LookupError as e:
        # bad gene query
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'Bad gene query.  Check your gene symbols: {0}.'.format(e.args[0])}, response)
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
        #print keyword_abstracts
    else:
        keyword_abstracts = None
    
    # get abstract ID's from index
    abstracts = abstracts_page(keywords, genes, usehomologs, limit, offset, orderby, onlyreviews, keyword_abstracts)
    
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

    # clean up gene symbols
    if genesyms:
        genesyms = ', '.join(set([s.strip() for s in genesyms.split(',') if s]))

    if orderby:
        orderby = orderby.lower()
    
    # turn onlyreviews into a boolean
    if onlyreviews:
        onlyreviews = parseboolean(onlyreviews)
        
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

    return render_to_response('abstractview.html', {'q':q,
        'species':species, 'genes':genes, 'genesyms': genesyms, 'geneop': geneop,
        'usehomologs':usehomologs, 'onlyreviews':onlyreviews, 
        'orderby':orderby, 'offset':offset,
        'unique':unique, 'abstractcount':abstractcount, 'rowgene':rowgene,
        'keywordnum': keywordnum, 'keywordstring': keywordstring,
        'gene_symbol_list': gene_symbol_list})
        
