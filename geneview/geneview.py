from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404

from genetext.geneview.event import EventInfo, get_events
from genetext.wordview.index import get_abstracts

def eventlist(request):
    
    # get genes out of request
    try:
        genes = [int(g) for g in request.GET['genes'].split(',')]
    except (AttributeError, ValueError):
        genes = None
    
    # get abstracts
    query = request.GET.get('q')
    if query:
        abstracts = getabstracts(query)
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
    
    #print "got args! getting events!", locals()
    
    events = get_events(genes=genes, abstracts=abstracts, limit=limit, offset=offset)
    
    #print "got events! Rendering!"
    
    return render_to_response("events.html", {'events':events})
    
def plot(request):
    try:
        id = int(request.GET['event'])
    except (AttributeError, ValueError):
        raise Http404
        
    ev = EventInfo(id)
    
    #print dir(ev)
    
    canvas = ev.plot()
    response = HttpResponse(content_type='image/png')
    canvas.print_png(response, dpi = 50)
    return response
