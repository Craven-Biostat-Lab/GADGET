from django.db.models import Count
import networkx as nx
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
#from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from pylab import figure, axes

from genetext.geneview.models import Abstract, Event, EventEvent, EventGene, Gene

def get_events(gene=None, genes=None, abstract=None, abstracts=None, mingenes = 1, offset=0, limit=None):
    """Return a list of events given a single gene, a single abstract, a list
    of genes, or a list of abstracts."""
    if gene is None and genes is None and abstract is None and abstracts is None:
        raise KeyError('You must supply either genes or abstracts to fetch events.')
    
    # if we have a single gene or abstract, make them into lists
    if gene:
        genes = (gene,)
    if abstract:
        abstracts = (abstract,)
    
    # build query 
    events = Event.objects.all()
    if genes:
        events = events.filter(allchildren__genes__id__in=genes)
    if genes and mingenes > 1:
        events = events.annotate(num_genes=Count('genes')).filter(num_genes__gte=mingenes)
    if abstracts:
        events = events.filter(abstracts__id__in=abstracts)

    # apply limit and offset
    if offset:
        events = events[offset:]
    if limit:
        events = events[:limit + offset]

    # execute query and return list of Event classes
    return [EventInfo(e.id) for e in events]

class EventInfo:
    """Represents a complex (root) event.  Event info is lazily fetched from the database."""
    
    # class variables: (not set until we need them, to minimize database load)
    # id - event root id.  passed during initialization.
    # events - all of the sub-events in the complex event (including the root event)
    # genes - a list of all genes in the event
    
    def __init__(self, root):
        self.id = root
        
    def get_id(self):
        return self.id
    
    def get_events(self):
        """Sub-events in the complex event (including the root event)"""
        try:
            return self.events
        except AttributeError:
            self.events = Event.objects.filter(root = self.id)
            return self.events
    
    def get_eventevents(self):
        try:
            return self.eventevents
        except AttributeError:
            self.eventevents = EventEvent.objects.filter(parent__in=self.get_events())
            return self.eventevents
        
    def get_genes(self):
        """All genes associated with this complex event."""
        try:
            return self.genes
        except AttributeError:
            self.genes = Gene.objects.filter(event__root=self.id)
            return self.genes
    
    def get_eventgenes(self):
        try:
            return self.eventgenes
        except AttributeError:
            self.eventgenes = EventGene.objects.filter(event__in=self.get_events())
            return self.eventgenes
            
    def get_abstracts(self):
        """Abstracts in which the root event is mentioned"""
        try:
            return self.abstracts
        except AttributeError:
            self.abstracts = Abstract.objects.filter(event = self.id)
            return self.abstracts
            
    def graph(self):
        """Construct and return a networkx graph of the event"""
        
        G = nx.DiGraph()
        
        queue = [] # keep events to be added in a queue
        
        eventtypes = dict([ ('e' + str(e.id), e.type) for e in self.get_events() ])
        
        roles = dict() # remember themes of each relationship (keyed on (parent, child) tuple)
        
        class multidict(dict):
            """Like a dictionary, but each key can have multiple values.
            (Each key returns a list of values.)"""
            def __setitem__(self, key, value):
                self.setdefault(key, []).append(value)
        
        # keep multidicts of children and parents for each event and gene
        children = multidict()
        parents = multidict()
        for ee in self.get_eventevents():
            parentname = 'e' + str(ee.parent.id)
            childname = 'e' + str(ee.child.id)
        
            children[parentname] = childname
            parents[childname] = parentname
            roles[(parentname, childname)] = ee.role
            
        for eg in self.get_eventgenes():
            evname = 'e' + str(eg.event.id)
            genename = 'g' + str(eg.gene.id)
            
            parents[genename] = evname
            children[evname] = genename
            roles[(evname, genename)] = eg.role
            if not evname in queue:
                queue.append(evname)
        
        # add genes as nodes
        G.add_nodes_from([('g' + str(g.id), {'label': g.symbol}) for g in self.get_genes()], gene=True)
        
        def has_all_children(ev):
            """Return true if all of the event's children are in the graph"""
            if ev not in children:
                return True
            else:
                for c in children[ev]:
                    if not G.has_node(c):
                        return False
                return True
                
        # iterate until the queue is empty (we have drawn all of the events)    
        while len(queue) > 0:
            # get the first event off the queue
            ev = queue.pop(0)
            
            # if the event has any child events not in the graph, 
            # requeue the event and the event's child events
            if not has_all_children(ev):
                queue.insert(0, ev)
                for c in children[ev]:
                    try: queue.remove(c)
                    except ValueError: pass
                    queue.insert(0,c)
            
            # If the event has no parents and has exactly 2 children, draw it as
            # an edge.  Otherwise draw it as a node with edges to its children.
            evargs = children[ev]
            if ev not in parents and len(evargs) == 2:
                # draw the event as an edge
                if roles[(ev, evargs[0])] == 'Cause' and roles[(ev, evargs[1])] == 'Theme':
                    G.add_edge(evargs[0], evargs[1], label=eventtypes[ev], directed=True)
                elif roles[(ev, evargs[0])] == 'Theme' and roles[(ev, evargs[1])] == 'Cause':
                    G.add_edge(evargs[1], evargs[0], label=eventtypes[ev], directed=True)
                else:
                    G.add_edge(evargs[0], evargs[1], label=eventtypes[ev], directed=False)
            else:    
                # if the event has parents, a number of arguments different than 2,
                # draw the event as a node with edges to its children
                G.add_node(ev, gene=False, label='')
                
                for a in evargs:
                    if roles[(ev,a)] == 'Theme':
                        G.add_edge(ev, a, label=eventtypes[ev], directed=True)
                    elif roles[(ev,a)] == 'Cause':
                        G.add_edge(a, ev, label=eventtypes[ev], directed=True)
            
            # queue the parents
            if ev in parents:
                for p in parents[ev]:
                    if p not in queue:
                        queue.append(p)
        return G
        
    def plot(self):
        G = self.graph()
        
        #fig = Figure()
        #ax = fig.add_subplot(111)
        fig = figure(figsize=(5, 3), dpi=65)
        ax = axes()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        
        pos = nx.spectral_layout(G) # node and edge positions
        
        directed_edges = [e for e in G.edges(data=True) if e[2]['directed']]
        undirected_edges = [e for e in G.edges(data=True) if not e[2]['directed']]
        
        node_size = [(300, 2000)[n[1]['gene']] for n in G.nodes(data=True)]
        node_color = [('purple', 'lightsteelblue')[n[1]['gene']] for n in G.nodes(data=True)]
        node_labels = dict([ (n[0], n[1]['label']) for n in G.nodes(data=True) ])
        
        edge_labels = dict([ ((e[0], e[1]), e[2]['label']) for e in G.edges(data=True) ])
        
        uG = G.to_undirected()
        
        nx.draw(G, pos=pos, ax=ax, hold=True, edgelist=directed_edges, node_size=node_size, 
            node_color=node_color, labels=node_labels)
        nx.draw_networkx_edges(uG, pos=pos, ax=ax, hold=True, edgelist=undirected_edges)
        nx.draw_networkx_edge_labels(G, pos=pos, ax=ax, edge_labels=edge_labels)
        
        canvas = FigureCanvas(fig)
        plt.close(fig)
        return canvas
