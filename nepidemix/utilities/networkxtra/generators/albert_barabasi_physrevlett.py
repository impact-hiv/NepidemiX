
"""

Albert-Barabasi network generator with varying connectivity probabilities
=========================================================================

Implementation of the Albert and Barabasi preferential attachment 
algorithm as described in 'Topology of Evolving Networks: Local Events and 
Universality', Physical Review Letters Vol 85, Number 24, 1999.

Experimental.

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

__all__ = ['albert_barabasi_physrevlett_quick', 
           'albert_barabasi_physrevlett_rigid']

import networkx as nx
import numpy
import random

# Logging
import logging

# Set up Logging
logger = logging.getLogger(__name__)

from ....exceptions import NepidemiXBaseException


def albert_barabasi_physrevlett_quick(N, m, m0 = None, p=0, q=0):
    """
    Implementation of the Albert and Barabasi preferential attachment 
    algorithm as described in 'Topology of Evolving Networks: Local Events 
    and Universality', Physical Review Letters Vol 85, Number 24, 1999.

    This version interprets the algorithm in such a way that it is always
    guaranteed to finish. The 'corners' that are cut are
    a) If no new link can be added in case i (i.e. saturated network) the
    algorithm gives up and continues having attached less than m links.
    (The rigorous interpretation would have the algorithm fail or start over
    from the beginning which may lead to extreme run times depending on p.)
    b) If one of the two nodes connected by the link in case ii has no other
    neighbor we do no update at all and continue. This not avoid creating
    disconnected graphs.
    
    
    Parameters
    ----------

    N : int
       Final network size, 
    
    m :int
       Number of links to add for each new node.
    
    m0 : int, optional
       Number of nodes in the original, simply connected graph.
       Requirement: m0 >= m
       if m0 == None, a default value of m will be used.
    
    p :float, optional
       Probability of adding m new links to the existing network

    q : float, optional
       Probability of rewiring m existing links in the network

    Returns
    -------

    G : networkx.Graph
       The resulting graph.

    Notes
    -----
    
    If p = q = 0 then the algorithm will default to the algorithm described in 
    'Emergence of Scaling in Random Networks' by Barabasi and Albert, 
    Science Vol 286, October 1999.
    
    
    """
    if m0 == None:
        m0 = m

    # Check input
    if m0 < m:
        raise NepidemiXBaseException(\
            "Parameter m0 needs to be larger or equal to m.")
    if not (p+q < 1):
        raise NepidemiXBaseException(\
            "It is necessary for 0 <= p + q < 1 for the network to grow.")
    if q < 0 or p <0 or q>=1 or p>=1:
        raise NepidemiXBaseException(\
            "Parameters p and q are probabilities and need to be in range [0,1)")
    # Take m number of nodes and create a simple connected network.
    G = nx.Graph()
    G.add_path(range(m0))
    # An array of node indexes. The number of indexes are proportional to 
    # the degree distribution of that node.
    nodeBasket = []
    # When we preferentially add new nodes, we want to keep the already
    # connected nodes away from the nodeBasket so that we can not choose
    # them. Store them here.
#    tempNodeBasket = []

    for n in G.nodes_iter():
        nodeBasket.extend([n]*(G.degree(n)+1))
    while G.number_of_nodes() < N:
        event_p = numpy.random.rand()
        if event_p < p:
            # Add a new preferential link to m existing nodes.
            # Chose a new node each time.
            for e in range(m):
                n = random.choice(G.nodes())
                __addlinksfrom(n, G, nodeBasket)
        elif event_p < (p + q):
            # (Preferentially) Rewire m links in the existing network.
            # Chose a new node each time.
            for e in range(m):
                n = random.choice(G.nodes())
                nn = random.choice(G.neighbors(n))
                if G.degree(n) > 1 and G.degree(nn) > 1:
                    # To avoid getting stuck and also disconnected graphs
                    # We only perform this IF the degree distribution of both
                    # nodes are greater than 1.
                    # Chose a new edge each time.
                    # Remove the link.
                    G.remove_edge(n, nn)
                    nodeBasket.remove(n)
                    nodeBasket.remove(nn)
                    __addlinksfrom(n, G, nodeBasket)
        else:
            # Add new node and m links to this node.
            # As this always result in the same new node
            # Chose it outside the loop.
            n = G.number_of_nodes()
            G.add_node(n)
            nodeBasket.append(n)
            for e in range(m):
                __addlinksfrom(n, G, nodeBasket)
                
    return G


def albert_barabasi_physrevlett_rigid(N, m, m0 = None, p=0, q=0):
    """
    Implementation of the Albert and Barabasi preferential attachment 
    algorithm as described in 'Topology of Evolving Networks: Local Events 
    and Universality', Physical Review Letters Vol 85, Number 24, 1999.

    Parameters
    ----------

    N : int
       Final network size, 
    
    m :int
       Number of links to add for each new node.
    
    m0 : int, optional
       Number of nodes in the original, simply connected graph.
       Requirement: m0 >= m
       if m0 == None, a default value of m will be used.
    
    p :float, optional
       Probability of adding m new links to the existing network

    q : float, optional
       Probability of rewiring m existing links in the network

    Returns
    -------

    G : networkx.Graph
       The resulting graph.

    Notes
    -----
    
    If p = q = 0 then the algorithm will default to the algorithm described in 
    'Emergence of Scaling in Random Networks' by Barabasi and Albert, 
    Science Vol 286, October 1999.

    """
    
    if m0 == None:
        m0 = m

    # Check input
    if m0 < m:
        raise NepidemiXBaseException(\
            "Parameter m0 needs to be larger or equal to m.")
    if not (p+q < 1):
        raise NepidemiXBaseException(\
            "It is necessary for 0 <= p + q < 1 for the network to grow.")
    if q < 0 or p <0 or q>=1 or p>=1:
        raise NepidemiXBaseException(\
            "Parameters p and q are probabilities and need to be in range [0,1)")
    
    # Take m0 number of nodes and create a simple connected network.
    G = nx.Graph()
    G.add_path(range(m0))
    # An array of node indexes. The number of indexes are proportional to 
    # the degree distribution of that node.
    nodeBasket = []

    for n in G.nodes_iter():
        nodeBasket.extend([n]*(G.degree(n)+1))
    while G.number_of_nodes() < N:
        event_p = numpy.random.rand()
        if event_p < p:
            # Add a new preferential link to m existing nodes.
            # Chose a new node each time.
            for e in range(m):
                n = random.choice(G.nodes())
                if __addlinksfrom(n, G, nodeBasket) == False:
                    return None
        elif event_p < (p + q):
            # (Preferentially) Rewire m links in the existing network.
            # Chose a new node each time.
            # If there's no edges to cut, fail.
            if G.number_of_edges() < 1:
                return None
            for e in range(m):
                nbrs = []
 #               logger.debug("Entering q while")
                while len(nbrs) < 1:
                    n = random.choice(G.nodes())
                    nbrs = G.neighbors(n)
                nn = random.choice(nbrs)
                G.remove_edge(n, nn)
                nodeBasket.remove(n)
                nodeBasket.remove(nn)
                if __addlinksfrom(n, G, nodeBasket) == False:
                    return None
        else:
            # Add new node and m links to this node.
            # As this always result in the same new node
            # Chose it outside the loop.
            n = G.number_of_nodes()
            G.add_node(n)
            nodeBasket.append(n)
            for e in range(m):
                if __addlinksfrom(n, G, nodeBasket) == False:
                    return None
                
    return G


def __addlinksfrom(n, G, nodeBasket):
    """
    Add links from node `n` in graph `G` to the nodes contained in 
    `nodeBasket`.
    
    Parameters
    ----------

    n : networkx node
       Node in `G`

    G : networkx.Graph
       Graph to work on

    nodeBasket : list of networkx nodes
       Neighbors of n will be randomly picked from this list.

    Returns
    -------
    success : bool
       True if the operation was successful. False else.

    """
    # Only do this if there's a chance to actually connect!
    if G.number_of_nodes() > 1+len(G.neighbors(n)):
        # There's always a chance that we connect preferentially to 
        # The same node as we started with. I.e trying to create a self
        # loop. Not allowed so we keep picking until we found another 
        # node.
        # In addition, keep picking until we have found a unconnected
        # preferential node. Note: This may take a LONG time, but should
        # be better on average than shoveling lists around.
        # The NetworkX implementation of the algorithm seems to ignore
        # if tries to connect links that is already there. Thus this will
        # be slower. However due to the outer if case we know that there
        # must be at least one disconnected (not linked) node. Thus we can 
        # not get stuck.
        pref_n = n
        nbrs = G.neighbors(n)
#        logger.debug("Entering add while nn={0}, len(nbrs) = {1}".format(G.number_of_nodes(), len(nbrs)))
#        if G.number_of_nodes() -2 <= len(nbrs):
#            logger.debug("graph = {2}; nbrs = {0}; n = {1}".format(nbrs, n, G.nodes()))
        while pref_n == n or (pref_n in nbrs):
            pref_n = random.choice(nodeBasket)
        G.add_edge(n, pref_n)
        nodeBasket.extend([n,pref_n])

        return True
    else:
        # Return false if there was no way to connect the node.
        return False
