from urllib import quote_plus
import json

from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.http import HttpResponse, Http404
from django.db.models import Sum, Count
from django import forms

import rpy2.robjects as robjects

from genetext.geneview.models import Gene, GeneAbstract, Abstract
from genetext.geneview.index import get_abstracts, corpus_size

def searchpage(request):
    """The search page for the word view (makes the forms)"""
    class SearchForm(forms.Form):
        q = forms.CharField(label='Keywords', initial='enter keywords')
        
    if request.GET.get('q'):
        q = request.GET['q']
        form = SearchForm(request.GET)
    else:
        q = ''
        form = SearchForm()
    
    # get the order from the query string
    orderby = request.GET.get('orderby', default='f1_score')
    
    return render_to_response('genesearch.html', {'form': form, 'q':q, 'orderby':orderby})


def genesearch(request):
    """Does the actual search for the word view.  Given a query (via the query
    string,) search the index for abstracts containing those terms, and then find
    and rank genes related to those abstracts."""
    
    # format to return the results in (blank for JSON to display in the browser)
    download = request.GET.get('download')
    
    # don't do anything if we don't have a query
    if not request.GET.get('q'):
        return searchresponse(validresult=False, download=download, errmsg="Please enter a query.")

    # get the abstracts matching our query 
    query = request.GET['q']
    abstracts = get_abstracts(query)
    total_abstracts = corpus_size()
    query_abstracts = len(abstracts)
    
    # error if there are no abstracts
    if query_abstracts == 0:
        return searchresponse(validresult=False, download=download, errmsg="Your query did not match any abstracts.", query=query)
        
    # get limit and offset from query string
    try: offset = int(request.GET.get('offset'))
    except: offset = 0
    
    try: 
        limit = int(request.GET.get('limit')) # limit to display to user
        query_limit = limit # limit to insert into SQL
    except: 
        limit = None
        query_limit = 18446744073709551615 # arbitrary large number (no better way to do this.)
    
    # dict of valid orderby options, and corresponding terms for SQL query
    _query_orderbys = {'adjusted_precision': 'precision',
        'matching_abstracts': 'hits', 'total_abstracts': 'abstracts',
        'f1_score': 'f1_score'}
    
    # get the order from the query string
    orderby = request.GET.get('orderby', default='f1_score')
    # make sure that the order-by option is valid, to prevent SQL injection
    if orderby not in _query_orderbys:
        orderby = 'f1_score'
    query_orderby = _query_orderbys[orderby] # orderby term to insert into SQL
        
    
    def paramstring(l):
        """Return a string of comma-separated %s's of length l
        (faster and more memory-efficient than using a list comprehension)"""
        def slist():
            for i in xrange(l): yield "%s"
        return ','.join(slist())
    
    # get genes matching query
    # raw sql: can't figure out how to do this efficiently with the Django API
    sqlquery = """
    SELECT g.*, 
        COUNT(*) hits, 
        COUNT(*)/ (`abstracts` + 10) `precision`,
        (2 * (COUNT(*) / `abstracts`) * (COUNT(*) / {query_abstracts})) / 
            ((COUNT(*) / `abstracts`) + (COUNT(*) / {query_abstracts})) f1_score
    FROM `gene_abstract` a
    INNER JOIN `gene` g
    ON g.id = a.gene
    WHERE a.`abstract_pmid` in ({paramstring})
    GROUP BY g.id
    ORDER BY `{orderby}` DESC
    LIMIT %s, %s;
    """.format(paramstring=paramstring(len(abstracts)), orderby=query_orderby, query_abstracts=query_abstracts)
    genes = Gene.objects.raw(sqlquery, abstracts + [offset, query_limit])
    
    # calculate p values
    phyper = robjects.r['phyper']
    pvals = ['{0:.2e}'.format(phyper(g.hits-1, query_abstracts, total_abstracts-query_abstracts, g.abstracts, lower_tail=False)[0]) for g in genes]

    # error if no results
    if not pvals: 
        return searchresponse(validresult=False, download=download, errmsg="Your query didn't match any genes.", query=query)
    
    return searchresponse(validresult=True, download=download, genes=genes, pvals=pvals, offset=offset, orderby=orderby, query=query, limit=limit)


def searchresponse(validresult, download=None, errmsg=None, genes=[], pvals=[], offset=0, orderby=None, query=None, limit=None):
    """Return an HttpResponse object with gene search results, as either JSON, XML,
    or a CSV depending on the "download" argument.  "validresult" is True if "genes",
    "pvals", and "offset" represent a valid result, and False otherwise.  "errmsg" 
    is an error message to display to the user."""

    if download:
        if not query: 
            raise Http404 # 404 if we don't have a query
    
        if download.lower() == 'csv':
            # create, package, and return a CSV file
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=gadget-{0}.csv'.format(quote_plus(query))
            response.write(makeCSV(genes, pvals, offset))
            return response
            
        elif download.lower() == 'xml':
            # render the XML template
            response = render_to_response('genelist.xml', 
                {'genes': zip(genes, pvals), 'pvals': pvals, 'offset': offset, 
                'orderby':orderby, 'q':query, 'limit':limit, 'errmsg': errmsg})
            response['Content-Type'] = 'text/xml'
            return response
            
        else:
            raise Http404 # 404 if invalid "download" argument
        
    else: # display results in web browser
        # render results to html
        if validresult:
            resulthtml = render_to_string('genelist.html', {'genes': zip(genes, pvals), 'pvals': pvals, 'offset': offset})
        else:
            resulthtml = None

        # render and return JSON
        response = HttpResponse()
        json.dump({'validresult': validresult, 'errmsg': errmsg, 'result': resulthtml}, response)
        return response


def makeCSV(genes, pvals, offset):
    """Create a CSV file (returned as a string) given a list of genes and a list of p values."""
    header = 'rank,f1_score,matching_abstracts,total_abstracts,adjusted_precision,p_value,symbol,name,synonyms,entrez_id,hgnc_id,ensembl_id,mim_id,hprd_id,chromosome,map_location\n'
    body = '\n'.join([','.join(['"{0}"'.format(f) for f in 
        (rank, '{0:0.3f}'.format(g.f1_score), g.hits, g.abstracts, '{0:0.3f}'.format(g.precision), p, g.symbol, g.name, g.synonyms, g.entrez_id, g.hgnc_id, g.ensembl_id, g.mim_id, g.hprd_id, g.chromosome, g.maplocation)])
        for rank, (g, p) in enumerate(zip(genes, pvals), start=1+offset)])
    return header + body


def abstracts(request):
    """Produce a list of abstracts for a gene and a query (also takes a limit and
    offset).  Render and return the "abstracts.html" template.  404 if bad input
    or no results."""
    
    # make sure we have the input we need, 404 if we don't
    try:
        query = request.GET['q']
        gene = int(request.GET['gene'])
    except ValueError:
        raise Http404
    
    # get optional limit and offset parameters
    try: offset = int(request.GET.get('offset'))
    except: offset = 0
    try: limit = int(request.GET.get('limit'))
    except: limit = 18446744073709551615 # arbitrary large number (no better way to do this.)
    
    # get the abstracts matching our query 
    queryabstracts = get_abstracts(query)
    
    # get abstracts tied to the gene
    abstracts = Abstract.objects.filter(geneabstract__gene=gene).filter(pubmed_id__in=queryabstracts)[offset:limit+offset]
    
    if abstracts:
        return render_to_response('abstracts.html', {'abstracts': abstracts})
    else: 
        raise Http404 # no results
