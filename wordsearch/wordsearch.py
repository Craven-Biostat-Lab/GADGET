from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.db.models import Sum, Count, F
from django import forms

from scipy.stats import hypergeom
from genetext.wordsearch.models import Gene, GeneAbstract
from genetext.wordsearch.index import getAbstracts, corpusSize

def search(request):
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
    SELECT g.*, COUNT(*) hits, COUNT(*)/`abstracts` score
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
    pvals = [1-hypergeom.cdf(g.hits, size, querycount, g.abstracts) for g in genes]
    #pvals = [0.5 for g in genes]
    
    if pvals:
        return render_to_response('result.html', {'genes': zip(genes, pvals), 'pvals': pvals, 'offset': offset})
    else:
        raise Http404 # no results
        
def makeCSV(genes):
    header = 'rank,score,symbol,name,aliases,old symbols,chromosome,accession,entrez,hugo,refseq,uniprot\n'
    body = '\n'.join([','.join(['"{0}"'.format(f) for f in 
        (i, '{0:0.2f}'.format(g.score), g.symbol, g.name, g.aliases, g.old_symbols, g.chromosome, g.accession, int(g.entrez), int(g.hugo), g.refseq, g.uniprot)])
        for i, g in enumerate(genes)])
    return header + body
