from urllib import quote_plus

from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.db.models import Sum, Count, F
from django import forms

import rpy2.robjects as robjects

from genetext.geneview.models import Gene, GeneAbstract, Abstract
from genetext.geneview.index import get_abstracts, corpus_size

def search(request):
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

def result(request):
    """Does the actual search for the word view.  Given a query (via the query
    string,) search the index for abstracts containing those terms, and then find
    and rank genes related to those abstracts."""
    
    if not request.GET.get('q'):
        raise Http404 # don't do anything if we don't have a query

    # get the abstracts matching our query 
    query = request.GET['q']
    abstracts = get_abstracts(query)
    total_abstracts = corpus_size()
    query_abstracts = len(abstracts)
    
    # 404 if there are no abstracts
    if query_abstracts == 0:
        raise Http404
    
    # get limit and offset from query string
    try: offset = int(request.GET.get('offset'))
    except: offset = 0
    try: limit = int(request.GET.get('limit'))
    except: limit = 18446744073709551615 # arbitrary large number (no better way to do this.)
    
    # get the order from the query string
    orderby = request.GET.get('orderby', default='f1_score')
    # make sure that the order-by option is valid, to prevent SQL injection
    if orderby not in ('precision', 'hits', 'abstracts', 'f1_score'):
        orderby = 'f1_score'
    
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
    """.format(paramstring=paramstring(len(abstracts)), orderby=orderby, query_abstracts=query_abstracts)
    genes = Gene.objects.raw(sqlquery, abstracts + [offset, limit])
    
    # calculate p values
    phyper = robjects.r['phyper']
    pvals = ['{0:.2e}'.format(phyper(g.hits-1, query_abstracts, total_abstracts-query_abstracts, g.abstracts, lower_tail=False)[0]) for g in genes]
    
    # return either a CSV (if "download" is in the query string,) an HTML page, or a 404       
    if pvals:
        if (request.GET.get('download')):
            # create, package, and return a CSV file
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=gadget-{0}.csv'.format(quote_plus(query))
            response.write(makeCSV(genes, pvals, offset))
            return response
        else:
            # if no "download", render HTML
            return render_to_response('genelist.html', {'genes': zip(genes, pvals), 'pvals': pvals, 'offset': offset, 'orderby':orderby})
    else:
        raise Http404 # no results
        
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
    
    try:
        query = request.GET['q']
        gene = int(request.GET['gene'])
    except ValueError:
        raise Http404 # don't do anything if we have bad input
    
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

def front(request):
    """The front page for the app"""  
    
    class GeneForm(forms.Form):
        q = forms.CharField(label='Keywords', initial='')
        
    class EventForm(forms.Form):
        q = forms.CharField(label='Keywords', initial='')
        genes = forms.CharField(label='Genes', initial='')    
        
    geneform = GeneForm()
    eventform = EventForm()
    
    return render_to_response('front.html', {'geneform': geneform, 'eventform': eventform})

