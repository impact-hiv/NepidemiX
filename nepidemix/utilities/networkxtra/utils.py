"""
NetworkX utility functions
==========================

A small set of utilities extending and operating on NetworkX graphs.


"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

__all__ = ["neighbors_data_iter", "attributeCount", "matchSetAttributes", 
           "matchDictAttributes", "entityCountSet", "entityCountDict", 
           "entityCount", "attributeValueDeal", "loadNetwork"]

import logging

import networkx as nx
import numpy as np

import random


# Set up Logging
logger = logging.getLogger(__name__)

def neighbors_data_iter(graph, n):
    """
    As networkX does not provide any good support o
    getting a nearest neighbour iterator with node data
    this is a utility function for doing just that.
    
    Parameters
    ----------

    graph :netwokx.Graph
       The graph

    n : networkx node
       A node in the graph.

    Returns
    -------

    iter : list iterator
       Iterator in the list of tuples (node, data) where node is a nearest 
       neighbour of n, and data is its associated attribute dictionary.
    
    Notes
    -----

    Is there a more efficient way of doing this?

    """
    return iter([(nn, graph.node[nn]) for nn in graph.neighbors_iter(n)])


def attributeCount(iterator, attr):
    """
    Count frequencies of a given set of possible values for some node or edge 
    attribute.
    
    Parameters
    ----------
   
    iterator : networkx.Graph.nodes_iter or networx.Graph.edges_iter 
       A networkx node or edge iterator. Note that the iterator functions must be called with data=True.
       Use `neighbour_data_iter` in this module to get an iterator over nearest neighbours.
    
    attr : hashable
       The name of the attribute to count.

    
    Returns
    -------
    
    scount :dict
       Dictionary of attribute value : count.

    """
    scount = {}
    for n in iterator:
        # Last item in tuple always the attributes.
        try:
            key = n[-1][attr]
        except KeyError:
            logger.error("Attribute {0} not in known list".format(key))
        scount[key] = scount.get(key,0) + 1
    return scount

def matchSetAttributes(vdict, vset):
    """
    This is a matching function used in entity count.
    In short it is designed to check if the attribute dictionary of a node or
    an edge has a specific set of keys, and if the matching values are any of
    the ones in a tuple.

    Note that the requirement is that the dictinary must contain all keys in the
    set and in adition that all the values must match the given options.

    Parameters
    ----------
    
    vset : set 
       Set of tuples (key, (val1,...,valn)). Key is a key, and the second
       value is a tuple of possible accept values for that key. 

    vdict :dict
       A dictionary of key:value pairs.

    Returns
    -------

    in : bool
       True if all keys in set match a key in dictionary and if 
       the dictionary values is contained in the set tuples.

    """
    for k,v in vset:
        if vdict.has_key(k) == False or vdict[k] not in v:
            return False
    return True

def matchDictAttributes(vdict0, vdict1):
    """
    This is a matching function used in entity count.
    Check if the key-value pairs of vdict1 is contained in vdict0.

    Parameters
    ----------

    vdict0 : dict
       Reference dictionary

    vdict1 : dict
       Query dictionary

    Returns
    -------

    isin : bool
      True if all keys in vdict1 is in vdict0 and if for all keys the values 
      match. 

    """
    for k,v in vdict1.iteritems():
        if vdict0.has_key(k) == False or vdict0.get(k) != v:
            return False
    return True


def entityCountSet(iterator, attributeSet):
    """
    Count the number of nodes/edges having an attribute dictionary which
    contains all the keys given in the attributeSet, and where the dictionary
    values for those keys matches a specific set of options.

    That is, the nodes/edges can have keys not contained in the set, 
    but not the other way around.

    Uses matchSetAttributes_

    Parameters
    ----------
    iterator :networkx.Graph iterator
       An iterator to a networx graph. Must have been created with data=True.
       
    attributeSet : set
       A set of (attribute, (value1, value2, value3,...)) tuples.

    Returns
    -------
    
    num : int
       Number of matching entities.
       
    """
    return entityCount(iterator, attributeSet, matchFunc = matchSetAttributes)

def entityCountDict(iterator, attributeDict):
    """
    Count the number of nodes/edges having an attribute dictionary which
    contains all the keys given in the attributeDict, and where the dictionary
    values for those keys matches the corresponding value in addributeDict.

    That is, the nodes/edges can have keys not contained in attributeDict, 
    but not the other way around.

    Uses matchDictAttributes_

    Parameters
    ----------
    iterator :networkx.Graph iterator
       An iterator to a networx graph. Must have been created with data=True.
       
    attributeDict : dict
       Reference dictionary.

    Returns
    -------
    
    num : int
       Number of matching entities.

    """
    return entityCount(iterator, attributeDict, matchFunc = matchDictAttributes)

def entityCount(iterator, attributes, matchFunc = matchSetAttributes):
    """
    Convenience function for entityCountSet and entityCountDict.

    Parameter
    ---------
    
    iterator : networkx.Graph iterator
       An iterator to a networx graph. Must have been created with data=True.

    attributes : dict or set
       As in either entityCountDict or entityCountSet

    matchFunc : function, optional
       Either matchDictAttributes, or matchSetAttributes
       Default: matchSetAttributes

    """
    s = 0
    for e in iterator:
        if matchFunc(e[-1], attributes):
            s += 1
    return s


        

def attributeValueDeal(iterator, attributeValues, graphSize, dealExact = False):
    """
    Deal values to a specific attribute of all nodes or edges in a graph.
    
    Parameters
    ----------

    iterator : networkx.Graph iterator
       A networkx node or edge iterator. Note that the iterator functions must 
       be called with data=True.

    attributeValues : list
       A list of tuples (AttDict, amount). Where AttDict is the attribute 
       dictionary to set and val is a number. If the sum of all val is equal to
       graphSize this exact number will be dealt. If not val will be normalized
       so that the sum is equal to graphSize.

    graphSize : int
       The number of nodes or edges that is to be initialized in the network. 
       Basically the number of items the iterator will acess.

    dealExact : bool, optional
       If set to True: Force the deal to match the exact number of values. I.e. if the number 
       of given attributes does not match the graph size it will be extended or
       decreased until it does. This could affect the distribution.
       If set to False: the number of values will be normalized by the graph size.
       Default value: False

    """
#    logger.debug("Att vals: {0}".format(attributeValues))
    if len(attributeValues) > 0:
        statePile = []

        vsum = float(np.sum([v for a,v in attributeValues]))
        if dealExact == True:
            # Only if the sum is larger than one AND if there are more than one element
            # Larger or equal to one.
            if vsum == 1 and (np.sum(np.array([v for a,v in attributeValues]) >= 1.0) >= 1)\
                    or vsum > 1.0:
                # Go over the states and numbers
                # Round to closest integer (should already be
                # integer, but just to be safe).
                for s,fr in attributeValues:
                    statePile.extend([s]*int(np.round(fr)))
            else:
                for s,fr in attributeValues:
                    statePile.extend([s]*int(np.round(fr*graphSize)))
        else:
            # Go through, and normalize by the sum.
            if vsum == graphSize:
                for s,fr in attributeValues:
                    statePile.extend([s]*int(np.round(fr)))
            else:
                for s,fr in attributeValues:
                    statePile.extend([s]*int(np.round((fr*graphSize)/vsum)))
            # In case the integer math has lead to some rounding error. Add a random state.
            # Should not skew things.
            while len(statePile) > graphSize:
                statePile.remove(random.choice(statePile))
            while len(statePile) < graphSize:
                statePile.append(random.choice(statePile))

#        logger.debug("State pile size: {0}; Gs: {1}".format(len(statePile), graphSize))
        # Loop over the nodes and assign state.
        for n in iterator:
            if len(statePile) > 0:
                v = random.choice(statePile)
                # Set values.
                # Last item in tuple is the nx dictionary.
                n[-1].update(v)
                statePile.remove(v)
               # logger.debug("Set {0}".format(n))
            else:
                break

def loadNetwork(file):
    """
    Utility function: Go through a number of file load methods and try to read 
    a graph.
    
    Currently tries gpickle and graphML.
    
    Parameters
    ----------
    
    file : str
       Name of file as string.

    Notes
    -----

       - Not very elegant as it relies on catching exceptions.
       - Could fail if two formats are overlapping.

    Returns
    -------
    G : networkx.Graph or None
       Returns the loaded graph or None if loading failed.

    """
    G = None
    iofail = False
    # gpickle
    if G == None and (not iofail):
        try:
            G = nx.readwrite.read_gpickle(file)
            logger.info("Read gpickle file '{0}'".format(f))
        except IOError:
            logger.error("Could not read file '{0}'".format(f))
            iofail = True
        except:
            pass

    # GraphML
    if G == None and (not iofail):
        try:
            G = nx.readwrite.read_graphml(file)
            logger.info("Read GraphML file '{0}'".format(f))
        except IOError:
            logger.error("Could not read file '{0}'".format(f))
            iofail = True
        except:
            pass
        
    return G


