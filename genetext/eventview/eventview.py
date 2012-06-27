import json
from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.http import HttpResponse, Http404
from django.db.models import Q
from django import forms

from genetext.eventview.event import EventInfo, get_events, get_event_genes, get_gene_combinations
from genetext.eventview.models import Gene
from genetext.abstracts.index import get_abstracts

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
    if query is None: return None
    query = [q.strip().upper() for q in query.split(',')]
    return Gene.objects.filter(symbol__in=query)

def eventlist(request):
    """Find and return events matching a query"""
    
    maxlimit = 500 # maximum number of events to fetch at once
    
    # get genes out of request.  First check for internal gene ids, then entrez
    # ids, then gene symbols.
    try:
        genes = [int(g) for g in request.GET['genes'].split(',')]
    except (KeyError, ValueError):
        try:
            gene_eids = [int(i.strip()) for i in request.GET['gene_entrez_ids'].split(',') if i != '']
            genes = [g.id for g in Gene.objects.filter(entrez_id__in=gene_eids)]
            
            # workaround for database mess
            if genes == []:
                raise Http404
        except (KeyError, ValueError):
            try:
                genes = [g.id for g in gene_lookup(request.GET['gene_symbols'])]
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
        if limit > maxlimit:
            limit = maxlimit
    except (KeyError, ValueError):
        limit = maxlimit
        
    try:
        offset = int(request.GET['offset'])
    except (KeyError, ValueError):
        offset = 0
    
    # get events, 404 if we don't supply either genes or abstracts
    try:
        events = get_events(genes=genes, abstracts=abstracts, limit=limit, offset=offset)
    except KeyError:
        events = []
    
    # return the appropriate response
    
    if request.GET.get('preview'):
        genesyms = [g.symbol for g in Gene.objects.filter(id__in=genes).only('symbol')] if genes else []
        
        # show more information about a specific gene
        # TODO: clean this up during the next re-organization of the event search
        detail = gene_lookup(request.GET.get('detail'))
        if len(detail) > 0:
            summaryrow = get_gene_combinations(genes=genes, abstracts=abstracts).get(detail[0].id)
            if summaryrow:
                summaryrow.innergenes.sort(key=lambda g: -g.count)
        else:
            summaryrow = None    
        
        return render_to_response("eventpreview.html", 
            {'events': events, 'geneids':genes, 'genesyms': genesyms, 'q': query, 'summaryrow':summaryrow})
    
    # 404 if there were no events
    if not events: 
        raise Http404
    
    dl = request.GET.get('download')
    if dl:
        if dl.lower() == 'xml':
            # return xml file
            
            response = HttpResponse('<?xml version="1.0" ?>\n<!DOCTYPE eventlist SYSTEM "http://gadget.biostat.wisc.edu/static/eventlist.dtd">\n<eventlist>\n')
            response.write(xmldescription(query=query, genes=genes, limit=limit, offset=offset))
            for ev in events:
                try:
                    # wrap each event in a try block so if something goes wrong,
                    # we still get all the other events.  take this out when debugging.
                    response.write('\n')
                    response.write(ev.xml(indent=2))
                except:
                    print "event {0} failed to render XML".format(ev.id)
            response.write('</eventlist>')
            
            response['Content-Type'] = 'text/xml'
            return response
        
        if dl.lower() == 'csv':
            # create, package, and return a CSV file
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=gadget-events.csv'
            response.write('event_id,gene_entrez_ids,gene_symbols,event_types,abstract_count\n'
                + '\n'.join([ev.tablerow() for ev in events]))
            return response
    
    # render HTML    
    return render_to_response("eventlist.html", {'events':events, 'q':query})


def eventgenes(request):
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
        
    # get genes, 404 if we don't supply either genes or abstracts
    try:
        event_genes = get_event_genes(genes=genes, abstracts=abstracts)
    except KeyError:
        raise Http404

    #return HttpResponse(event_genes)
    
    if event_genes:
        return render_to_response("eventgenes.html", {'event_genes': event_genes, 'genes':genes})
    else:
        raise Http404

def eventsummary(request):
    response = HttpResponse()
    
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
        
    # get gene combinations
    try:
        outergenes = get_gene_combinations(genes=genes, abstracts=abstracts)
    except KeyError:
        # error if no gene or abstracts
        json.dump({'validresult': False, 'errormsg': 'You must supply either genes or a keyword query'}, response)
        return response
    
    # get sorter function from request
    orderby = request.GET.get('orderby', 'abstracts').lower()    
    sorter = {'abstracts': lambda g: -g.count, 'symbol': lambda g: g.symbol}[orderby]

    # sort data structure before rendering it
    outergenes_sorted = []
    for og in sorted(outergenes.values(), key=sorter):
        og.innergenes.sort(key=sorter)
        outergenes_sorted.append(og)
   
    # apply limit
    try:
        limit = int(request.GET.get('limit'))
        outergenes_sorted = outergenes_sorted[:limit]
    except (TypeError, ValueError):
        pass
   
    # render and return JSON response
    if outergenes_sorted:
        json.dump({'validresult': True, 
            'result': render_to_string("eventsummary.html", 
            {'outergenes': outergenes_sorted, 'genes': genes, 'orderby': orderby})}, response)
    else:
        json.dump({'validresult': False, 'errormsg': 'No genes found'}, response)
    return response

def thumb(request):
    """Return a smaller plot of each event"""
    return plot(request, dpi=40)
    
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

def xmldescription(**kwargs):
    """Given keyword arguments, make a description to include in XML results."""
    desc = '  <description>\n'
    
    for k,v in sorted(kwargs.items()):
        if v:
            if k == 'genes':
                # genes get special treatment
                genes = Gene.objects.filter(id__in=v)
                desc += '    <genelist>\n'
                for g in genes:
                    desc += '      <gene>\n'
                    desc += '        <entrez_id>{0}</entrez_id>\n'.format(g.entrez_id)
                    desc += '        <symbol>{0}</symbol>\n'.format(g.symbol)
                    desc += '      </gene>\n'
                desc += '    </genelist>\n'
                
            else:
                desc += '    <{0}>{1}</{0}>\n'.format(k,v)
            
    return desc + '  </description>'
    
def xml(request):
    try:
        id = int(request.GET['event'])
    except (KeyError, ValueError):
        raise Http404
    
    ev = EventInfo(id)
    return HttpResponse('<?xml version="1.0" ?>\n' + ev.xml())
