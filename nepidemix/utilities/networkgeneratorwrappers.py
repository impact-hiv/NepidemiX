"""
Network creation wrapper classes
================================

As the parameter values read from configuration file (currently)
is type independent we need a way to map to types accepted by the graph
generation functions.
The current best solution is to create wrappers that maps to the right type.

An alternative approach would be to require explicit type casting in the
configuration file.

A wrapper is simply an instance of the NetworkGenerator class providing a
function for creating the network and a dictionary of (name, type) pairs.

This module could be made obsolete if using a configuration system with explicit 
types. 

Examples
--------

Creating a wrapper object is done by creating a specific instance of the 
`NetworkGenerator` class and providing a reference to its `create` method.
So, for instance to create a wrapper for the networkx function 
`barabasi_albert_graph`, that accepts the two parameters `n` and `m`, both of
type `int` one would do::
   
   BA_networkx = NetworkGenerator(networkx.barabasi_albert_graph, {"n":int, "m":int}).create

The name `BA_networkx` could then be used in configuration.

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

__all__ = ["NetworkGenerator"]

import networkx as nx

from networkxtra.generators import *

import networkxtra.utils as nwxutils


class NetworkGenerator(object):
    """
    Network generation wrapper object.
    
    """
    
    def __init__(self, creationFunction, typeMap):
        """

        Parameters
        ----------
        creationFunction : function
           Function used to create a networkx graph.

        typeMap : dict
           Dictionary of the structure (<parameter name>, <type>) so that
           the the parameter is a parameter to creationFunction and <type>
           is a type object.

        """
        self.creationFunction = creationFunction
        self.typeMap = typeMap

    def create(self, **kwargs):
        """
        This method will call `function` given when creating the 
        `NetworkGenerator` after type casting the parameters as specified 
        in `typeMap`.

        Parameters
        ----------
        
        kwargs : special
           The general argument dictionary for the network creation function.
           Note that the argument list must precisely match the one for
           creation function.
        
        Returns
        -------

        result : special
           The result from calling `function`.

        
        See Also
        --------

        NetworkGenerator.__init__ : constructor

        """
        for k,v in self.typeMap.items():
            kwargs[k] = v(kwargs[k])
        return self.creationFunction(**kwargs)
        

# Specific instances created for convenience
#--------------------------------------------

# Wrapper function for the networkx implementation of the BA algorithm.
barabasi_albert_graph_networkx = NetworkGenerator(nx.barabasi_albert_graph, {"n":int, "m":int}).create
# NOTE: old version. Kept for backward comp. will be removed in future. Use above instead.
BA_networkx = NetworkGenerator(nx.barabasi_albert_graph, {"n":int, "m":int}).create


# Wrapper function for the implementation of the Albert and Barabasi alg. in
# Phys. Rev. Letters.
albert_barabasi_prv_quick = NetworkGenerator(albert_barabasi_physrevlett_quick,
                                             {"N":int, "m":int, "p":float, "q":float})\
                                             .create                                             
# NOTE: old version. Kept for backward comp. will be removed in future. Use above instead.
AB_phys_rev_letters_quick = NetworkGenerator(albert_barabasi_physrevlett_quick,
                                             {"N":int, "m":int, "p":float, "q":float})\
                                             .create

grid_2d_graph_networkx = NetworkGenerator(nx.grid_2d_graph,
                                          {'m':int, 'n':int}).create

fast_gnp_random_graph_networkx = NetworkGenerator(nx.fast_gnp_random_graph,
                                                  {'n':int, 'p':float}).create

load_network = NetworkGenerator(nwxutils.loadNetwork, {'file':str}).create

connected_watts_strogatz_graph_networkx = NetworkGenerator(nx.connected_watts_strogatz_graph,
                                                  {'n':int, 'k':int, 'p':float}).create
# NOTE: old version. Kept for backward comp. will be removed in future. Use above instead.
connected_watts_strogatz_graph = NetworkGenerator(nx.connected_watts_strogatz_graph,
                                                  {'n':int, 'k':int, 'p':float}).create

powerlaw_cluster_graph_networkx = NetworkGenerator(nx.powerlaw_cluster_graph,
                                          {'n':int, 'm':int, 'p':float}).create
# NOTE: old version. Kept for backward comp. will be removed in future. Use above instead.
Holme_and_Kim_powerlaw = NetworkGenerator(nx.powerlaw_cluster_graph,
                                          {'n':int, 'm':int, 'p':float}).create

powerlaw_degree_sequence = NetworkGenerator(powerlaw_degree_sequence,
                                            {"n":int, "a":float}).create

toivonen = NetworkGenerator(toivonen_standard, 
                            {"N_0":int, "N":int, "k":int}).create
