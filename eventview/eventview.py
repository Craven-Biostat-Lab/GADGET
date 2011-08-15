from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.db.models import Q
from django import forms

from genetext.eventview.event import EventInfo, get_events
from genetext.eventview.models import Gene
from genetext.geneview.index import get_abstracts

def search(request):
    """The event search page.  Creates and reads from the forms."""
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
        geneids = None
        genesyms = None
    
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
    
    # get events, 404 if we don't supply either genes or abstracts
    try:
        events = get_events(genes=genes, abstracts=abstracts, limit=limit, offset=offset)
    except KeyError:
        raise Http404
    
    if events:
        if request.GET.get('preview'):
            genesyms = [g.symbol for g in Gene.objects.filter(id__in=genes).only('symbol')]
            return render_to_response("eventpreview.html", 
                {'events': events, 'geneids':genes, 'genesyms': genesyms, 'q': query})
        else:
            return render_to_response("eventlist.html", {'events':events, 'q':query})
    else:
        raise Http404

def thumb(request):
    """Return a smaller plot of each event"""
    return plot(request, dpi=35)
    
def plot(request, dpi=65):
    try:
        id = int(request.GET['event'])
    except (KeyError, ValueError):
        raise Http404
        
    ev = EventInfo(id)
    
    canvas = ev.plot(dpi=dpi)
    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response
