from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.db.models import Sum
from django import forms

from genetext.wordsearch.models import Gene, Word, GeneWord

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
    if request.GET.get('q'):
        # get matching genes
        query = request.GET['q'].lower().split()
        genes = Gene.objects.filter(geneword__word__word__in=query).annotate(score=Sum('geneword__weight')).order_by('-score')
        
        # get limit and offset
        try: offset = int(request.GET.get('offset'))
        except: offset = 0
        try: limit = int(request.GET.get('limit'))
        except: limit = None
        if limit:
            genes = genes[offset : offset+limit]
        
        if (request.GET.get('download')):
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=results.csv'
            response.write(makeCSV(genes))
            return response
        else:
            if genes:
                return render_to_response('result.html', {'genes': genes, 'offset': offset})
            else:
                raise Http404 # no results
    else: raise Http404 # no query
        
def makeCSV(genes):
    header = 'rank,score,symbol,name,aliases,old symbols,chromosome,accession,entrez,hugo,refseq,uniprot\n'
    body = '\n'.join([','.join(['"{0}"'.format(f) for f in 
        (i, '{0:0.2f}'.format(g.score), g.symbol, g.name, g.aliases, g.old_symbols, g.chromosome, g.accession, int(g.entrez), int(g.hugo), g.refseq, g.uniprot)])
        for i, g in enumerate(genes)])
    return header + body
