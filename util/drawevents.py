#!/usr/bin/python

import MySQLdb
import networkx as nx
import matplotlib.pyplot as plt
from random import randint

# connect to database
db = MySQLdb.connect(user='root', passwd='password', db='turku')
c = db.cursor()

def getchildren(event):
    """Lookup the children of an event from the database (given an event ID.)
    Return 5 things: 1) the type of the event, 2) a list of child event ID's,
    3) a list of child event roles, 4) a list of child gene symbols, 5) a list
    of child gene roles"""
    
    # look up event type   
    c.execute("""SELECT `type` from homologene_event where id = %s""", event)
    eventtype = c.fetchone()[0]
    
    # get child event ID's and roles
    c.execute("""SELECT `role`, `arg_homologene_event_id`
        from homologene_eventargument_event
        where homologene_event_id = %s""", event)
    rows = c.fetchall()
    if rows: eventroles, events = zip(*rows)
    else: eventroles, events = [], []
    
    # get child gene symbols and roles
    c.execute("""SELECT `role`, `homologene_id`
        from homologene_eventargument_ggp 
        where homologene_event_id = %s""", event)
    rows = c.fetchall()
    if rows: generoles, genes = zip(*rows)
    else: generoles, genes = [], []
    
    return eventtype, events, eventroles, genes, generoles
    
def buildeventgraph(event):
    """Build and return a graph of an event's structure, given the event ID"""
    
    G = nx.DiGraph() # graph of event
    G.add_node(event, event=True)
    
    queue = [event] # add new events to queue
    
    while len(queue) > 0:
        cur = queue.pop(0)
        eventtype, events, eventroles, genes, generoles = getchildren(cur)
        
        G.node[cur]['type'] = eventtype
        
        G.add_nodes_from(events, event=True)
        G.add_edges_from([ (cur, e, {'role':r}) for e, r in zip(events, eventroles) ])
        queue.extend(events)

        G.add_nodes_from([ (g, {'type': g}) for g in genes ], event=False)
        #G.add_nodes_from(genes, event=False)
        G.add_edges_from([ (cur, g, {'role':r}) for g, r in zip(genes, generoles) ])
        
    return G
    
def draweventgraph(G):
    """Draws and labels a graph for an event.  (Doesn't show or save the graph though.)"""

    nodelabels = dict([ (n[0], n[1]['type']) for n in G.nodes(data=True) ])
    nodecolors = [ n[1]['event'] for n in G.nodes(data=True) ]
    edgelabels = dict([ ((e[0], e[1]), e[2]['role']) for e in G.edges(data=True) ])
    pos = nx.spectral_layout(G)

    plt.cla()
    nx.draw(G, pos=pos, labels=nodelabels, node_color=nodecolors, cmap=plt.cm.Paired, alpha=0.75, node_size=800)
    nx.draw_networkx_edge_labels(G, pos=pos, edge_labels=edgelabels, font_size=8)
    
if __name__ == '__main__':
    from sys import argv
    
    if argv[1] == 'sample':
        # look up 50 random events and plot them
        for i in xrange(50):
            
            c.execute("""select max(id) from homologene_event;""")
            maxid = c.fetchone()[0]
            
            # grab a random event (make sure it exists)
            while True:
                event = randint(0, maxid)
                c.execute("""select * from homologene_event where id = %s;""", event)
                if len(c.fetchall()) == 1:
                    break
                    
            G = buildeventgraph(event)
            draweventgraph(G)
            plt.savefig('eventgraphs/{0}.png'.format(event))
        
    else:
        # show one individual graph
        event = int(argv[1])

        G = buildeventgraph(event)
        draweventgraph(G)
        plt.show()


