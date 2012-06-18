#!/usr/bin/python
import json

from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from django.shortcuts import render_to_response

from genetext.geneview.geneview import gene_lookup, parseboolean
from genetext.abstracts.index import abstracts_page
from genetext.geneview.models import Abstract

def abstracts(request):
    """Return a list of abstracts (as HTML wrapped in JSON) for a keyword
    query and list of genes."""

    # get species, default=human
    try:
        species = int(request.GET['species'])
    except (KeyError, ValueError):
        species = 9606
    
    # get query arguments from query string
    keywords = request.GET.get('q')
    try:
        genes = gene_lookup(request.GET.get('genes'), species)
    except KeyError:
        # bad gene query
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'Bad gene query.  Check your gene symbols.'}, response)
        return response
    
    # figure out if we should include homologs
    try:
        usehomologs = parseboolean(request.GET['usehomologs'])
    except (KeyError, ValueError):
        usehomologs = False
    
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
    
    # get abstract ID's from index
    abstracts = abstracts_page(keywords, genes, usehomologs, limit, offset, orderby, onlyreviews)
    
    # error if no abstracts
    if not abstracts:
        response = HttpResponse()
        json.dump({'validresult': False, 'errmsg': 'No more abstracts!'}, response)
        return response
    
    
    # fetch rows from database
    #abstracts = Abstract.objects.filter(pubmed_id__in=abstract_ids)
   
    # create response
    resulthtml = render_to_string('abstracts.html', {'abstracts': abstracts})
    response = HttpResponse()
    json.dump({'validresult': True, 'result': resulthtml}, response)
    return response


def abstractview(request):
    """Render the container page for displaying abstracts"""
    q = request.GET.get('q')
    species = request.GET.get('species')
    genes = request.GET.get('genes')
    usehomologs = request.GET.get('usehomologs')
    onlyreviews = request.GET.get('onlyreviews')
    orderby = request.GET.get('orderby')
    offset = request.GET.get('offset')
    unique = request.GET.get('unique')
    abstractcount = request.GET.get('abstractcount')


    if orderby:
        orderby = orderby.lower()
    if onlyreviews:
        onlyreviews = parseboolean(onlyreviews)

    return render_to_response('abstractview.html', {'q':q,
        'species':species, 'genes':genes, 'usehomologs':usehomologs,
        'onlyreviews':onlyreviews, 'orderby':orderby, 'offset':offset,
        'unique':unique, 'abstractcount':abstractcount})
