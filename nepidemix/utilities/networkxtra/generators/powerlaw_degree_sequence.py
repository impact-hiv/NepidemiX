"""
Poweralaw degree network generation
===================================

Implementation of a simple 'power law degree-sequence' approach to generating
graphs. Basically just creating a degree sequence with a given exponent
and then letting networkx create a graph. Afterwards self-loops and parallel edges
are removed so there is no guarantee that the exact degree will be kept for finite
networks. 

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

__all__ = ['powerlaw_degree_sequence']

import networkx as nx

import logging
# Set up Logging
logger = logging.getLogger(__name__)


from ....exceptions import NepidemiXBaseException


def powerlaw_degree_sequence(n, a):
    """
    Create a graph without self-loops or parallel edges; having power law degree
    distribution with an exponent 'around' a.
    
    Parameters
    ----------

    n : int
       Number of nodes in graph.
       
    a : float
       Ideal exponent.

    Returns
    -------
    
    G : networkx.Graph
       The constructed graph.

    """
    dsq = nx.create_degree_sequence(n, nx.utils.powerlaw_sequence, exponent = a)
    G = nx.Graph(nx.configuration_model(dsq))
    G.remove_edges_from(G.selfloop_edges())
    
    # Check for a disconnected graph just in case...
    if not nx.is_connected(G):
        emsg = "The generated power-law graph is not connected!"
        logger.error(emsg)
        raise NepidemiXBaseException(emsg)

    return G
    
