from matplotlib import use
use('Agg') # set matplotlib backend

from django.db.models import Count
import networkx as nx
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.pyplot as plt
from pylab import figure, axes

from genetext.eventview.models import Abstract, Event, EventEvent, EventGene, Gene
from django.core.cache import cache

def get_events(genes=None, abstracts=None, offset=0, limit=None):
    """Return a list of event ID's given gene ID's and/or abstract ID's"""
    
    if genes is None and (abstracts is None or len(abstracts) == 0):
        raise KeyError('You must supply either genes or abstracts to fetch events.')
    
    # build query, order by increasing compleity (number of sub-events)
    events = Event.objects.distinct().annotate(ev_count=Count('allchildren__event')).order_by('ev_count')
    
    # restrict events by matching genes and abstracts
    if genes:
        for g in genes:
            events = events.filter(allchildren__event__genes__id=g)
    if abstracts:
        events = events.filter(abstracts__pubmed_id__in=abstracts, allchildren__event__isnull=False)

    # apply limit and offset
    if offset:
        events = events[offset:]
    if limit:
        events = events[:limit + offset]

    # execute query and return list of Event classes
    events = [EventInfo(e.id) for e in events]
    
    #from django.db import connection
    #queries = connection.queries
    #raise Exception
    
    return events

def get_event_genes(genes, abstracts):
    """Return genes"""
    
    if genes is None and (abstracts is None or len(abstracts) == 0):
        raise KeyError('You must supply either genes or abstracts to fetch events.')
    
    def build_sql(genes=None, abstracts=None):
        
        params = [] # list of all the parameters we're sending to the server
        
        def paramstring(l):
            """Return a string of comma-separated %s's of length l
            (faster and more memory-efficient than list comprehensions)"""
            def slist():
                for i in xrange(l): yield "%s"
            return ','.join(slist())
        
        # first part of query.  do a subquery of events matching the genes and 
        # abstracts, then get matching genes.
        query = \
        """
        select
        g.id, g.symbol, count(distinct e_root.id) ev_count
        from gene g
        inner join event_gene eg
        on eg.gene = g.id
        inner join event_root er
        on er.event = eg.event
        inner join (
            select e_root.id
            from event e_root
        """
        
        # join in abstracts to event subquery
        if abstracts:
            query += \
            """
            inner join event_abstract ea
            on ea.event = e_root.id
            """
        
        # join in genes.  only get root events.  if there are abstracts, handle
        # them in here (because of the order MySQL wants query clauses)
        if genes:
            query += \
            """
            inner join event_root er
            on e_root.id = er.root
            inner join event_gene eg
            on eg.event = er.event
            where eg.gene in ({paramstring})
            """.format(paramstring=paramstring(len(genes)))
           
            params += genes
            
            # restrict events to matching abstracts
            if abstracts:
                query += \
                """
                and ea.abstract_pmid in ({paramstring})
                """.format(paramstring=paramstring(len(abstracts)))
                params += abstracts
            
            # count the matching genes to see if we have all genes in the query
            # (instead of one join to the event_gene table for each gene)
            query += \
            """
            group by e_root.id
            having count(distinct eg.gene) >= {0}
            """.format(len(genes))
            
        # restrict events to matching abstracts (if we didn't already do it)
        if abstracts and not genes:
            query += \
            """
            where ea.abstract_pmid in ({paramstring})
            group by e_root.id
            """.format(paramstring=paramstring(len(abstracts)))
            params += abstracts
        
        # join in the subquery of matching events
        query += \
        """    
        ) e_root
        on e_root.id = er.root
        group by g.id
        order by ev_count desc, g.symbol asc;
        """
    
        return query, params
    
    query, params = build_sql(genes, abstracts)

    #raise Exception    
    
    ev_genes = Gene.objects.raw(query, params)
    return ev_genes
    
    
class EventInfo:
    """Represents a complex (root) event.  Event info is lazily fetched from the database."""
    
    # class variables: (not set until we need them, to minimize database load)
    # id - event root id.  passed during initialization.
    # events - all of the sub-events in the complex event (including the root event)
    # genes - a list of all genes in the event
    
    def __init__(self, root):
        cached = cache.get('e_' + str(root))
        if cached:
            self.__dict__ = cached.__dict__
        else:
            self.id = root
    
    def __del__(self):
        """Save a copy of the event in the cache when garbage collected."""
        cache.set('e_' + str(self.id), self, 90)
    
    def get_events(self):
        """Sub-events in the complex event (including the root event)"""
        try:
            return self.events
        except AttributeError:
            self.events = Event.objects.filter(roots = self.id)
            return self.events
    
    def get_eventevents(self):
        try:
            return self.eventevents
        except AttributeError:
            #self.eventevents = EventEvent.objects.filter(parent__in=self.get_events())
            self.eventevents = EventEvent.objects.filter(parent__roots=self.id)
            return self.eventevents
        
    def get_genes(self):
        """All genes associated with this complex event."""
        try:
            return self.genes
        except AttributeError:
            self.genes = Gene.objects.filter(event__roots=self.id).only('id', 'symbol')
            return self.genes
    
    def get_eventgenes(self):
        try:
            return self.eventgenes
        except AttributeError:
            #self.eventgenes = EventGene.objects.filter(event__in=self.get_events())
            self.eventgenes = EventGene.objects.filter(event__roots=self.id)
            return self.eventgenes
            
    def get_abstracts(self):
        """Abstracts in which the root event is mentioned"""
        try:
            return self.abstracts
        except AttributeError:
            self.abstracts = Abstract.objects.filter(event=self.id)
            return self.abstracts
            
    def get_abstract_count(self):
        try:
            return self.abstract_count
        except AttributeError:
            try:
                self.abstract_count = len(self.abstracts)
                return self.abstract_count
            except AttributeError:
                self.abstract_count = Abstract.objects.filter(event=self.id).count()
                return self.abstract_count
            
            
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
                    if not G.has_node(c):
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
        
    def plot(self, dpi=65):
        G = self.graph()
        
        #fig = Figure()
        #ax = fig.add_subplot(111)
        fig = figure(figsize=(6, 3), dpi=dpi, frameon=False)
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
        
    def xml(self, indent=0, tabwidth=2):
        """Return an XML representation of the event (as a string).  Indent is 
        the initial indent for the first element, tabwidth is the amount of 
        additional indent for each child element."""
        
        def print_event(ev, i=0, abstract_count=False):
            # open event tag
            x = (' '*i) + '<event id="{0}">\n'.format(ev.id)
            x += (' ' * (i+tabwidth)) + '<type>{0}</type>\n'.format(ev.type)
            
            if abstract_count:
                x += (' ' * (i+tabwidth)) + '<abstract_count>{0}</abstract_count>\n'.format(self.get_abstract_count())
            
            # print eventgenes
            for eg in self.get_eventgenes():
                if eg.event == ev:
                    x += print_eventgene(eg, i + tabwidth)
            
            # print eventevents
            for ee in self.get_eventevents():
                if ee.parent == ev:
                    x += print_eventevent(ee, i + tabwidth)
            
            # close event tag
            x += (' '*i) + '</event>\n'
            return x
        
        def print_gene(g, i=0):
            x = (' '*i) + '<gene>\n'
            
            x += (' ' * (i + tabwidth)) + '<entrez_id>{0}</entrez_id>\n'.format(g.entrez_id)
            x += (' ' * (i + tabwidth)) + '<symbol>{0}</symbol>\n'.format(g.symbol)
            
            x += (' '*i) + '</gene>\n'
            return x

        def print_eventevent(ee, i=0):
            # open tag
            x = (' '*i) + '<{0}>\n'.format(ee.role.lower())
            
            # find child event
            ev = [ev for ev in self.get_events() if ev.id == ee.child.id][0]
            x += print_event(ev, i + tabwidth)
            
            # close tag
            x += (' '*i) + '</{0}>\n'.format(ee.role.lower())
            return x
        
        def print_eventgene(eg, i=0):
            x = (' '*i) + '<{0}>\n'.format(eg.role.lower())
            
            # find gene
            g = [g for g in self.get_genes() if g.id == eg.gene.id][0]
            x += print_gene(g, i + tabwidth)
            
            x += (' '*i) + '</{0}>\n'.format(eg.role.lower())
            
            return x
            
        ev, = [ev for ev in self.get_events() if ev.id == self.id]
        return print_event(ev, i=indent, abstract_count=True)
        
    def tablerow(self):
        """Return a table-row representation of self"""
        
        geneids = '|'.join([str(g.entrez_id) for g in self.get_genes()])
        genesyms = '|'.join([g.symbol for g in self.get_genes()])
        eventtypes = '|'.join([ev.type for ev in self.get_events()])
        
        return ','.join((str(self.id), geneids, genesyms, eventtypes, str(self.get_abstract_count())))
