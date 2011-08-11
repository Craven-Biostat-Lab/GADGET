from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.db.models import Q
from django import forms

from genetext.eventview.event import EventInfo, get_events
from genetext.eventview.models import Gene
from genetext.geneview.index import get_abstracts

def search(request):
    class SearchForm(forms.Form):
        q = forms.CharField(label='Keywords', initial='')
        genes = forms.CharField(label='Genes', initial='')
    
    if request.GET.get('q') or request.GET.get('genes'):
        form = SearchForm(request.GET)
        go = True
        q = request.GET.get('q')
        
        if request.GET.get('genes'):
            genes = gene_lookup(request.GET['genes'])
            geneids = [g.id for g in genes]
            genesyms = [g.symbol for g in genes]
        else:
            genes = None
            geneids = None
            genesyms = None
            
    else:
        form = SearchForm()
        go = False
        q = None
        genes = None
        genequery = None
    
    return render_to_response('eventsearch.html', {'form': form, 'go': go, 
        'q':q, 'geneids':geneids, 'genesyms':genesyms})
        
def gene_lookup(query):
    """Given a string of genes separated by commas, lookup and return
    gene ID's from Entrez ID's and symbols."""
    query = [q.strip().upper() for q in query.split(',')]
    return Gene.objects.filter(symbol__in=query)

def eventlist(request):
    
    # get genes out of request
    try:
        genes = [int(g) for g in request.GET['genes'].split(',')]
    except (KeyError, ValueError):
        genes = None
    
    # get abstracts
    query = request.GET.get('q')
    if query:
        abstracts = get_abstracts(query)
    else:
        abstracts = None
    
    # get limit and offset
    try:
        limit = int(request.GET['limit'])
    except (KeyError, ValueError):
        limit = None
    try:
        offset = int(request.GET['offset'])
    except (KeyError, ValueError):
        offset = 0
    
    events = get_events(genes=genes, abstracts=abstracts, limit=limit, offset=offset)
    
    from django.db import connection
    with open('queries', 'w') as f:
        f.write(repr(connection.queries))
    
    if events:
        return render_to_response("eventlist.html", {'events':events, 'q':query})
    else:
        raise Http404
    
def plot(request):
    try:
        id = int(request.GET['event'])
    except (KeyError, ValueError):
        raise Http404
        
    ev = EventInfo(id)
    
    #print dir(ev)
    
    canvas = ev.plot()
    response = HttpResponse(content_type='image/png')
    canvas.print_png(response, dpi = 50)
    return response
