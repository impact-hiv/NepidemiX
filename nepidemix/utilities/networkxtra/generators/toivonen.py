"""
Toivonen et al. network generator for social network models
===========================================================

Implementation of the network generation algorithm described in 
'A Model for Social Networks' by Riitta Toivonen et al. 
Arxiv ID: arXiv:physics/0601114v2

Experimental.

"""

__author__ = "Lukas Ahrenberg"

__license__ = "Modified BSD License"

__all__ = ['toivonen_standard', 'generalized_toivonen']

import networkx as nx
import numpy as np
import random

from ....exceptions import NepidemiXBaseException

def toivonen_standard(N_0, N, k):
    """
    Simplified interface to the Toivonen algorithm.
    Based on the examples given in the paper, a simply connected ring of N_0 
    elements is used as a seed graph and grown until it reaches the size N.
    One primary node is selected with probability 0.95, and two primary nodes 
    w.p. 0.05.
    Secondary nodes (nearest neighbors of the primary node) are picked 
    uniformly at random. A minimum of 0 and a maximum of k nodes are picked
    for each primary node.

    Parameters
    ----------

    N_0 : int
       Size of the seed graph.
       The graph will be grown from N_0 simply connected nodes.
    N : int
       Size of the final graph.
    k : int
       Maximum number of secondary links.
       The number of secondary neighbors to link to in each step is picked
       from the uniform distribution U[0,k] (inclusive).
    """

    # Check arguments
    if not (N_0 > 0):
        raise( NepidemiXBaseException(
            "Seed graph size must be greater than zero."
        ) )
    if not (N_0 < N):
        raise( NepidemiXBaseException(
            "Seed graph size must be less than target graph size."
        ) )

    if not (k > 0):
        raise( NepidemiXBaseException(
            "Number of maximum secondary connections must be greater than zero."
        ) )

    # Create empty graph.
    graph = nx.Graph()
    # Create simply connected ring.
    for n in range(1,N_0):
        graph.add_edge(n-1, n)
    graph.add_edge(0,k)
    
    # One primary node with probability 0.95, two primary nodes w.p. 0.05
    m_r = [(1,0.95), (2, 0.05)]
    # Create a uniform distribution with k+1 members.
    m_s = zip(range(0,k+1),[1.0/(k+1)]*(k+1))
    
    return generalized_toivonen(graph, N, m_r, m_s)

def generalized_toivonen(graph, target_size, mr_distribution, ms_distribution):
    """
    
    Parameters
    ----------
    
    graph : NetworkX graph
       A non empty graph that will be used as a seed and grown using the 
       Toivonen algorithm. The size of graph corresponds to $N_0$ in the paper.
       Note that the graph will be modified.
    
    target_size : int
       The target size of the network, $N$ in the paper.

    mr_distribution : array of tuples
       A distribution of the probability to choose a specific number of initial contacts.
       In the paper this corresponds to the probabilities 
       $p(n_{\mbox{init}} = 1), p(n_{\mbox{init}} = 2), ...$
       This information is encoded in the array as a tuple (n,p_n) where n 
       denotes the initial number of contacts and p_n the probability to pick
       this number. 
       E.g. $p(n_{\mbox{init}} = 1) = 0.95, p(n_{\mbox{init}} = 2) = 0.05$ as
       used in the paper would be encoded as the array [(1, 0.95), (2, 0.05)] .
       The probabilities in the array must add up to one.
       The expected value corresponds to $m_r$ in the paper.

    ms_distribution : array of tuples
       A distribution of the probability to choose a specific number of 
       secondary contacts. A secondary contact is a neighbor of the initial
       contact.
       This information is encoded in the array as a tuple (n,p_n) where n 
       denotes the initial number of contacts and p_n the probability to pick
       this number.
       For instance, in the paper the uniform distribution U[0,3] is used.
       This would be encoded as 
       [(0, 1.0/4.0), (1, 1.0/4.0), (2, 1.0/4.0), (3, 1.0/4.0)].
       The expected value corresponds to $m_s$ in the paper.
    """
    
    # Checks
    if target_size <= 0:
        raise( NepidemiXBaseException(
            "Graph target size must be > 0."
            ) )

    if graph.number_of_nodes() >= target_size:
        raise( NepidemiXBaseException(
            "Seed graph is greater than target graph size."
            ) )

    # Compute cumulative distributions from prob. arrays and
    # check so they add up to 1.0.
    # Also compute expected value.
    mr_c = []
    cp = 0.0
    mr_exp = 0.0
    for n,p in mr_distribution:
        cp += p
        mr_exp += n*p
        mr_c.append( (n,cp))
    if cp < 1.0 or cp > 1.0:
        raise( NepidemiXBaseException(
            "Probabilities in mr_distribution does not add up to 1.0."
            ))

    ms_c = []
    cp = 0.0
    ms_exp = 0.0
    for n,p in ms_distribution:
        cp += p
        ms_exp += n*p
        ms_c.append( (n,cp))
    if cp < 1.0 or cp > 1.0:
        raise( NepidemiXBaseException(
            "Probabilities in ms_distribution does not add up to 1.0."
            ))

    # Will hold the total number of primary nodes accessed.
    n_primary_added = 0.0
    # Will hold the total number of secondary nodes accessed.
    n_secondary_added = 0.0
    # Will hold the total number of new nodes added.
    n_new_nodes = 0.0

    # Grow network
    # as long as the graph has less nodes than the target value.
    while graph.number_of_nodes() < target_size:
        
        # Create a node and add it. Node IDs sequential range of integers.
        new_node_id = graph.number_of_nodes()
        graph.add_node(new_node_id)
        n_new_nodes += 1

        # Pick a number of first hand contacts determined
        # by the PDF given n mr_distribution.
        for primary_index in range(0, __pickfrom(mr_c)):
            n_primary_added += 1
            # Pick an initial node from the sequence of all ints except
            # the newly added (which is one larger)
            primary_node_id = random.randint(0,new_node_id - 1)            
            # Don't add an edge to the new node yet,
            # because now edges will be added to its neighbors.

            # Create pool of neighbors of the primary_node to serve as 
            # secondary node candidates.
            primary_neighbors = graph.neighbors(primary_node_id)
            
            # Of these we optimally want to pick a number determined by
            # the PDF ms_distribution, however the number of neighbors
            # may be fewer than this number so we pick the min.
            n_secondary = min(__pickfrom(ms_c),len(primary_neighbors))

            for secondary_index in range(0, n_secondary):
                n_secondary_added += 1
                # Pick a random neighbor
                secondary_node_id = random.choice(primary_neighbors)
                # Remove it from pool
                primary_neighbors.remove(secondary_node_id)
                # Create edge
                graph.add_edge(new_node_id, secondary_node_id)
            
            # Finally, all secondary links are in place, and we close by creating a link to 
            # the primary node.
            graph.add_edge(new_node_id, primary_node_id)
            
    # Finished. Return the graph, the expected values, and the true averages 
    # for primary and secondary contacts.
    return graph, \
        mr_exp, \
        ms_exp, \
        n_primary_added / n_new_nodes, \
        n_secondary_added / n_primary_added

def __pickfrom(cdf_array):
    
    # Pick a random number (0,1]
    p = random.random()
    indx = 0
    # Loop until the cdf part is less.
    while p > cdf_array[indx][1]:
        indx+=1
    # Return the corresponding n.
    return cdf_array[indx][0]
