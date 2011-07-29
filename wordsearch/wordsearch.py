from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.db.models import Sum, Count, F
from django import forms

import rpy2.robjects as robjects

from genetext.wordsearch.models import Gene, GeneAbstract, Abstract
from genetext.wordsearch.index import getAbstracts, corpusSize

def search(request):
    """The search page for the word view (makes the forms)"""
    class SearchForm(forms.Form):
        q = forms.CharField(label='Keywords:', initial='enter keywords')
        
    if request.GET.get('q'):
        q = request.GET['q']
        form = SearchForm(request.GET)
    else:
        q = ''
        form = SearchForm()
    
    return render_to_response('search.html', {'form': form, 'q':q})

def result(request):
    """Does the actual search for the word view.  Given a query (via the query
    string,) search the index for abstracts containing those terms, and then find
    and rank genes related to those abstracts."""
    
    if not request.GET.get('q'):
        raise Http404 # don't do anything if we don't have a query

    # get the abstracts matching our query 
    query = request.GET['q']
    abstracts = getAbstracts(query)
    size = corpusSize()
    querycount = len(abstracts)
    
    # get limit and offset from query string
    try: offset = int(request.GET.get('offset'))
    except: offset = 0
    try: limit = int(request.GET.get('limit'))
    except: limit = 18446744073709551615 # arbitrary large number (no better way to do this.)
    
    # create a string of '%s,'s to insert into the SQL query to pass the abstracts
    def paramlist(s): 
        for i in xrange(s): yield '%s'
    paramstring = ','.join(paramlist(len(abstracts)))
    
    # get genes matching query
    # raw sql: can't figure out how to do this efficiently with the Django API
    sqlquery = """
    SELECT g.*, COUNT(*) hits, COUNT(*)/ (`abstracts` + 1) score
    FROM `gene_abstract` a
    INNER JOIN `gene` g
    ON g.id = a.gene
    WHERE a.`abstract_pmid` in ({paramstring})
    GROUP BY g.id
    ORDER BY score DESC
    LIMIT %s, %s;
    """.format(paramstring=paramstring)
    genes = Gene.objects.raw(sqlquery, abstracts + [offset, limit])
    
    # calculate p values
    phyper = robjects.r['phyper']
    pvals = [1-phyper(g.hits, querycount, size-querycount, g.abstracts)[0] for g in genes]
    
    # return either a CSV (if "download" is in the query string,) an HTML page, or a 404
    if (request.GET.get('download')):
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=results.csv'
        response.write(makeCSV(genes, pvals))
        return response
    else:
        if pvals:
            return render_to_response('result.html', {'genes': zip(genes, pvals), 'pvals': pvals, 'offset': offset})
        else:
            raise Http404 # no results
        
def makeCSV(genes, pvals):
    """Create a CSV file given a list of genes and a list of p values."""
    header = 'rank,score,p_value,symbol,name,synonyms,entrez_id,hgnc_id,ensembl_id,mim_id,hprd_id,chromosome,map_location\n'
    body = '\n'.join([','.join(['"{0}"'.format(f) for f in 
        (rank, '{0:0.3f}'.format(g.score), '{0:0.5f}'.format(p), g.symbol, g.name, g.synonyms, g.entrez_id, g.hgnc_id, g.ensembl_id, g.mim_id, g.hprd_id, g.chromosome, g.maplocation)])
        for rank, (g, p) in enumerate(zip(genes, pvals))])
    return header + body

def abstracts(request):
    """Produce a list of abstracts for a gene and a query."""
    
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
    queryabstracts = getAbstracts(query)
    
    # get abstracts tied to the gene
    abstracts = Abstract.objects.filter(geneabstract__gene=gene).filter(pubmed_id__in=queryabstracts)[offset:limit+offset]
    
    if abstracts:
        return render_to_response('abstracts.html', {'abstracts': abstracts})
    else: 
        #return HttpResponse("<li>yo!")
        raise Http404 # no results
    
