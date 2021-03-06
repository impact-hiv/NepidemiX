
"""
=========
Processes
=========

A process operates on a network/graph and has the ability to change node and edge states as well as network topology.

All NepidemiX processes should be subclasses of the interface Process.

Methods need to be specified for updating the network and for loading settings.
"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

from exceptions import *

from utilities import networkxtra

from utilities.linkedcounter import LinkedCounter

import numpy

import networkx

import nepidemix as nepx

import math

import collections

import copy

# Logging
import logging

# Set up Logging
logger = logging.getLogger(__name__)

__all__ = ['Process', 'AttributeStateProcess', 'ExplicitStateProcess', 
           'ScriptedProcess', 'ScriptedTimedProcess']

class Process(object):
    """
    Base class/interface for a NepidemiX process.
    
    As a general network is just a collection of nodes and edges it is up
    to the process specification to determine how node and edge states are
    represented. Each process model could in theory operate on its own 
    interpretation of these entities. This flexibility however means that it
    must also be up to the process to initialize the network and to deduce
    unique names for node and edge states for the simulation.
    
    When defining a process inherit from this interface and overload appropriate 
    methods from the list below. You should only ignore overloading methods for
    which entities your process will leave unchanged. E.g. if your process don't
    have any edge states you may safely ignore the 'Edge'-methods, or if you
    know that there will be no global network topology changes leave the 
    'networkUpdateRule'.
    
    It is seldom necessary to derive directly from Process. Consider 
    nepidemix.ExplicitStateProcess which represents states as a python 
    dictionary and have the initialization and deduce-methods filled in.

    Notes
    -----
    
    **List of methods to overload**

    nodeUpdateRule(...)
       For state changes to individual nodes.
    edgeUpdateRule(...)
       For state changes to individual edges.
    networkUpdateRule(...)
       For global network state changes, such as topology changes.
    initializeNetworkNodes(...)
       Network node initialization to boundary conditions.
    initializeNetworkEdges(...)
       Network node initialization to boundary conditions.
    initializeNetwork(...)
       Perform initialization of global network conditions.
    deduceNodeState(...)
       From whatever representation the process has of a node return its state.
    deduceEdgeState(...)
       From whatever representation the process has of an edge return its 
       state.

    See method documentation for interface specifications.

    **List of class attributes that affects simulation**

    runNodeUpdate
       If set True the simulation will execute nodeUpdateRule for each node
       in each iteration. If false the update will be skipped.
    runEdgeUpdate
       If set True the simulation will execute edgeUpdateRule for each edge
       in each iteration. If false the update will be skipped.
    runNetworkUpdate
       If set True the simulation will execute meanFieldUpdateRule for in 
       each iteration. If false the update will be skipped.
    constantTopology
       If set to True this indicates to the simulation that the network 
       topology remains unchanged between iterations, and indicates to the
       Simulation that it may optimize by not running some undefined 
       updates. If set to false a full topology copy will be performed and
       this also overrides any run[Node/Edge/Network]Update flags set to 
       False, forcing the updates.

    """
    def __init__(self, 
                 runNodeUpdate = True, 
                 runEdgeUpdate = True,
                 runNetworkUpdate = True,
                 constantTopology = False):
        """
        Parameters
        ----------

        runNodeUpdate : bool, optional
           If set True the simulation will execute nodeUpdateRule for each node
           in each iteration. If false the update will be skipped.
           Default value: True

        runEdgeUpdate :  bool, optional
           If set True the simulation will execute edgeUpdateRule for each edge
           in each iteration. If false the update will be skipped.
           Default value: True

        runNetworkUpdate : bool, optional
           If set True the simulation will execute meanFieldUpdateRule for in 
           each iteration. If false the update will be skipped.
           Default value: True

        constantTopology : bool, optional
           If set to True this indicates to the simulation that the network 
           topology remains unchanged between iterations, and indicates to the
           Simulation that it may optimize by not running some undefined 
           updates. If set to false a full topology copy will be performed and
           this also overrides any run[Node/Edge/Network]Update flags set to 
           False, forcing the updates.
           Default value: False

        """
        self.runEdgeUpdate = runEdgeUpdate
        self.runNodeUpdate = runNodeUpdate
        self.runNetworkUpdate = runNetworkUpdate
        self.constantTopology = constantTopology


    

    def nodeUpdateRule(self, node, srcNetwork, dt):
        """
        Perform local node changes.
        This method is called once per node per iteration in the simulation.
        The state of `node` and `srcNetwork` is that of the previous iteration.
        After execution node is expected to be updated and returned in the 
        new state.

        This method needs to be overloaded in any sub classes. Its purpose is to
        make attribute changes to a single node at the time and it should ONLY
        make changes to node alone.

        Parameters
        ----------
        
        node : networkx node, Structure: (<node id>, {<attribute name-value map>})
           This is a copy of the current node and the target of any changes.
           
        srcNetwork : networkx.Graph
           A networkX graph, with the original nodes. Will remain unchanged.
        
        dt : float
           Time differential (float) as a fraction of time unit (since last 
           update).
        
        Returns
        -------

        node : networkx node
           `node` with changes

        """
        return node

    def edgeUpdateRule(self, edge, srcNetwork, dt):
        """
        Perform local edge change.

        This method is called for each edge in the network during each time
        step of the simulation.
        The state of `edge` and `srcNetwork` is that of the previous simulation iteration.
        This method is expected to make any update to edge and return it in
        its new state.
        Overload this method when constructing a process.

        Parameters
        ----------

        edge :  networkx edge, Structure (<node id 1>, <node id 2>, <attribute dict>)
           This is a copy of the current edge in the simulation and will be the
           target of any changes.

        srcNetwork :  networkx.Graph
           The network where the edge lived during last iteration. 
           Should be treated as constant.

        dt : float
           Time differential since last iteration.

        Returns
        -------
        
        edge : networkx edge, `edge` with changes.

        """
        return edge

    def networkUpdateRule(self, network, dt):
        """
        Perform update to global network structure and attributes.
        
        This method is called for the network once after it has been updated 
        using the node and edge update rules.
        It should be used to update global network attributes.
        It should not change any node or edge states on individual levels.
        Used for mean field states etc.
        Overload this method when building a process.

        Parameters
        ----------

        network : networkx.Graph
           The network, work on this object and return it.

        dt :  float
           Time differential since last iteration.

        Returns
        -------
        
        network : networkx.Graph, The updated network

        """
        return network

    def initializeNetworkNodes(self, network, *args, **kwargs):
        """
        Set initial states and parameters to a network.

        This method should be overloaded for each individual process to 
        initialize network states and parameters on a given network. This is 
        because while topology is a feature of the network, only the process 
        will know how to initialize it.
        
        Parameters
        ----------

        network : networkx.Graph
           The network to initialize.

        args,kwargs : special
           Additional parameters may be passed using **kwargs by the calling
           simulation object if they are declared in the configuration.
           This mechanism should be used to build general initialization methods.

        Returns
        -------

        network : networkx.Graph, `network`
           While he method should work directly on network it should also return it.

        """
        return network

    def initializeNetworkEdges(self, network, *args, **kwargs):
        """
        Set initial edge states and parameters to a network.
        
        This method should be overloaded for each individual process to initialize
        network edge states and parameters on a given network. This is because while
        topology is a feature of the network, only the process will know how to
        initialize it.
        
        Parameters
        ----------

        network : networkx.Graph
           The network to initialize.

        args,kwargs : special
           Additional parameters may be passed using **kwargs by the calling
           simulation object if they are declared in the configuration.
           This mechanism should be used to build general initialization methods.

        Returns
        -------

        network : networkx.Graph, `network`
           While he method should work directly on network it should also return it.

        """
        return network


    def initializeNetwork(self, network, *args, **kwargs):
        """
        Perform initialization on global network options.
        
        Called after node and edge initialization. Should if overloaded update
        the dictionary in network.graph[Simulation.STATE_COUNT_FIELD_NAME] so
        that it contains the number of nodes/edges in each state used by the
        process.

        May be used for instance in setting up mean field states.

        Parameters
        ----------

        network : networkx.Graph
           The network to initialize.

        args,kwargs : special
           Additional parameters may be passed using **kwargs by the calling
           simulation object if they are declared in the configuration.
           This mechanism should be used to build general initialization methods.

        Returns
        -------

        network : networkx.Graph, `network`
           While he method should work directly on network it should also return it.

        """
        return network

    def deduceNodeState(self, node):
        """
        Gives the state of a node.
        
        Overload this method to provide a state given a node in a network.

        This is based on the design assumption that we have a finite number
        of states in which a node may reside at any point in time.
        Internally however a process may or may not explicitly keep track of
        in which state a node currently is. (For instance there may be a large
        number of parameters associated with a node, and not an explicit state.)
        
        This method is responsible of returning the state of a given node structure
        according to the process. For processes explicitly keeping track of the state
        it only needs to return said state. For other types of processes some calculations
        may be necessary. The resulting state should be a hashable object.

        Parameters
        ----------
        
        node : networkx node
           Structure: (<node id>, {<attribute name-value map>})

        Returns
        -------

        state : hashable
           The method should in some way come up with a state descriptor from
           from `node` and return it. The state representation must be a hashable
           object.
        
        """
        return None

    def deduceEdgeState(self, edge):
        """
        Gives the state of an edge.
        
        Overload this method to provide a state given a edge in a network.

        This is based on the design assumption that we have a finite number
        of states in which an edge may reside at any point in time.
        Internally however a process may or may not explicitly keep track of
        in which state an edge currently is. (For instance there may be a large
        number of parameters associated with a edge, and not an explicit state.)
        
        This method is responsible of returning the state of a given edge structure
        according to the process. For processes explicitly keeping track of the state
        it only needs to return said state. For other types of processes some calculations
        may be necessary.

        Parameters
        ----------

        edge : networkx edge
           Structure (<node id 1>, <node id 2>, <attribute dict>)

        Returns
        -------
        
        state : hashable
           The method should in some way come up with a state descriptor from
           from `edge` and return it. The state representation must be a hashable
           object.

        """
        return None


class ExplicitStateProcess(Process):
    """
    This class is a specialization of `Process` that assumes that all
    states are explicitly stored  (as opposed as derived from a set of 
    attributes) and given when the class is initialized.
   
    The nodes and edges will all have attributes named after the value of 
    ExplicitStateProcess.STATE_ATTR_NAME and the rule methods are supposed 
    to update this filed with the new state.
    
    Used for convenience to collect a number of similar methods for all
    subclasses.

    A deriving class need only to overload the __init__ and/or any of the
    *UpdateRule methods that will be used.


    See Also
    --------

    Process : Superclass

    """

    # The reserved name for the state attribute in the network nodes.
    STATE_ATTR_NAME = "state"

    def __init__(self, nodeStates, edgeStates,
                 runNodeUpdate = True, 
                 runEdgeUpdate = True, 
                 runNetworkUpdate = True,
                 constantTopology = False):
        """
        Will make sure that the class knows about the states listed in 
        `nodeStates` and `edgeStates`.
        
        The node and edge states may be accessed through the class member lists
        `nodeStateIds` and `edgeStateIds`
        If you subclass and overload this method make sure to use super to call 
        it.

        Parameters
        ----------
        
        nodeStates : set 
           set containing all valid node state identifiers

        edgeStates : set 
           set containing all valid edge state identifies
           
        runEdgeUpdate : bool
           See Process

        runNodeUpdate : bool
           See Process
        
        runNetworkUpdate : bool 
           See Process

        constantTopology : bool
           See Process

        """
        super(ExplicitStateProcess, self).__init__(runNodeUpdate, runEdgeUpdate, runNetworkUpdate, 
                                                   constantTopology)
        self.nodeStateIds = list(set(nodeStates))
        self.edgeStateIds = list(set(edgeStates))
        if nodeStates != None:
            self.nodeStateIndexMap = {}
            for ind in range(len(self.nodeStateIds)):
                self.nodeStateIndexMap[self.nodeStateIds[ind]] = ind
        if edgeStates != None:
            self.edgeStateIndexMap = {}
            for ind in range(len(self.edgeStateIds)):
                self.edgeStateIndexMap[self.edgeStateIds[ind]] = ind

    def initializeNetwork(self, network, *args, **kwargs):
        """
        Initialize the mean field states on the network.
        
        Parameters
        ----------
        
        network : networkx.Graph
           The network on which the process will run.
           
        Returns
        -------
        
        network : networkx.Graph
           `network` with updated attributes. Each additional attribute
           being a mean field state corresponding to a node/edge state.

        See Also
        --------
           Process : Superclass

        """ 
        # Set the network attribute counters to the edge and node states.
        if len(self.nodeStateIds) > 0:
            c = networkxtra.attributeCount(
                network.nodes_iter(data=True),
                self.STATE_ATTR_NAME)
            network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME].update(c)

        if len(self.edgeStateIds) > 0:
            c = networkxtra.attributeCount(
                network.edges_iter(data=True),
                self.STATE_ATTR_NAME)
            network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME].update(c)
        
    
    def initializeNetworkNodes(self, network, *args, **kwargs):
        """
        Set initial node states and parameters to a network.
        
        This implementation of initializeNetworkNodes assumes that it is passed
        the fraction/amount of nodes in each state as additional arguments.
        That is the parameter name must be a valid node state as declared 
        when the object is initialized and the value of the parameter must be
        an integer or a float. If all parameter values add up to the
        number of nodes in `network` the exact number of nodes in that state
        will be randomly distributed. If the sum is not the number of nodes the
        number of nodes in a particular state will be proportional to that number.
        
        Parameters
        ----------

        network : networkx.Graph 
           The network to initialize

        kwargs : special
           One parameter name per state in the process model the value of which
           should be a number.

        Returns
        -------

        network : networkx.Graph
           The updated `network` object with node state distributed.

        See Also
        --------

        Process : Superclass

        """
        # All values should be floats, so let's convert them at this stage.
        nodeAttDict = [({self.STATE_ATTR_NAME:s},float(v)) for s,v in kwargs.iteritems()]
        # Check so the given arguments matches the state names we have.
        if not (frozenset(kwargs.keys()) \
                    == frozenset(self.nodeStateIds)):
            errMsg = "States given in config section '{0}' ({1}) does not match node states defined in network process ({2})."\
                .format(nepx.simulation.Simulation.CFG_SECTION_NODE_STATE_DIST, 
                        frozenset(kwargs.keys()), 
                        frozenset(self.nodeStateIds))
            logger.error(errMsg)
            raise NepidemiXBaseException(errMsg)
        # Distribute the states.
        networkxtra.attributeValueDeal(network.nodes_iter(data=True),nodeAttDict, 
                                             network.number_of_nodes())
      
        # Finally just add a symbol for the mean field of any states that may
        # have ended up with a distribution of zero entities in the first round
        # (because they were rounded down or set to zero perhaps).
        # Just to keep count.
        for k in kwargs:
            if not network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME].has_key(k):
                network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME][k] = 0

        return network

    def initializeNetworkEdges(self, network, *args, **kwargs):
        """
        Set initial edge states and parameters to a network.
        
        This implementation of initializeNetworkEdges assumes that it is passed
        the fraction/amount of edges in each state as additional arguments.
        That is the parameter name must be a valid edge state as declared 
        when the object is initialized and the value of the parameter must be
        an integer or a float. If all parameter values add up to the
        number of edges in `network` the exact number of edges in that state
        will be randomly distributed. If the sum is not the number of edges the
        number of edges in a particular state will be proportional to that number.
        
        Parameters
        ----------

        network : networkx.Graph 
           The network to initialize

        kwargs : special
           One parameter name per state in the process model the value of which
           should be a number.

        Returns
        -------

        network : networkx.Graph
           The updated `network` object with edge state distributed.

        See Also
        --------

        Process : Superclass

        """
        
        # All values should be floats, so let's convert them at this stage.
        edgeAttDict = [(s,float(v)) for s,v in kwargs.iteritems()]
        # Check so the given arguments matches the state names we have.
        if not (frozenset(kwargs.keys()) \
                    == frozenset(self.edgeStateIds)):
            errMsg = "States given in config section '{0}' ({1}) does not match edge states defined in network process ({2})."\
                .format(nepx.simulation.Simulation.CFG_SECTION_EDGE_STATE_DIST, 
                        frozenset(kwargs.keys()), 
                        frozenset(self.edgeStates()))
            logger.error(errMsg)
            raise NepidemiXBaseException(errMsg)

        # Distribute the states.
        networkxtra.attributeValueDeal(network.edges_iter(data=True), 
                                             edgeAttDict, 
                                             network.number_of_edges())
        
        # Finally just add a symbol for the mean field of any states that may
        # have ended up with a distribution of zero entities in the first round
        # (because they were rounded down or set to zero perhaps).
        # Just to keep count.
        for k in kwargs:
            if not network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME].has_key(k):
                network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME][k] = 0
        
        return network


    def deduceNodeState(self, node):
        """
        Gives the state of a node.
        
        Will return the corresponding node state declared when initializing
        the object.
        
        Parameters
        ----------

        node : networkx node, Structure (<node id>, {<attribute name-value map>})
        
        Returns
        -------
        
        state : hashable
           The state associated with `node`.
           
        See Also
        --------
        
        Process : Superclass

        """
        # This is an explicit state process, so we can just return it.
        return node[1].get(self.STATE_ATTR_NAME)
    
    
    def  deduceEdgeState(self, edge):
        """
        Gives the state of a edge.
        
        Will return the corresponding edge state declared when initializing
        the object.
        
        Parameters
        ----------

        edge : networkx edge, Structure (<node id 1>, <node id 2>, <attribute dict>)
        
        Returns
        -------
        
        state : hashable
           The state associated with `edge`.
           
        See Also
        --------
        
        Process : Superclass

        """
        # This is an explicit state process, so we can just return it.
        return edge[2].get(self.STATE_ATTR_NAME)
        
    


class AttributeStateProcess(Process):
    """
    This class is a specialization of `Process` where node and edge states are 
    determined from associated attribute dictionary. As a returned state must 
    be hashable it is defined as the frozen set of the attribute dictionary.
    Methods that take state names as parameters do this as strings formatted
    as python dictionaries (thus describing the attribute dictionary).
    
    When initialized this class require a declaration of all possible 
    attribute names, and all possible values those attributes may be set to.

    Used for convenience to collect a number of similar methods for all
    subclasses.

    A deriving class need only to overload the __init__ and/or any of the
    *UpdateRule methods that will be used.


    See Also
    --------
    Process : Superclass
    
    """
    # A special parameter for the configuration.
    CFG_PARAM_deal_exact = 'deal_exact'

    def __init__(self, 
                 nodeAttributeDict, 
                 edgeAttributeDict,
                 meanFieldStates,
                 runNodeUpdate = True, 
                 runEdgeUpdate = True, 
                 runNetworkUpdate = True,
                 constantTopology = False):
        """
        Initialize an object of this class by giving all possible node and edge
        state values.
        
        If you subclass and overload this method make sure to use super to call 
        it.
        
        Parameters
        ----------
    
        nodeAttributeDict : dict
           A dictionary where key:val pair is the name of 
           the node attribute and a tuple of all its possible values.
           Example: {'age': (1,2,3,4), 'colour': ('red','green')} denotes
           a process where nodes have two attributes (age, and colour).
           The first one can take one out of four different values
           and the second one of two values. This result in a network
           with 4*2=8 different node states.

        edgeAttributeDict : dict 
           A dictionary where key:val pair is the name of 
           the edge attribute and a tuple of all its possible values.
           Example: {'age': (1,2,3,4), 'colour': ('red','green')} denotes
           a process where edges have two attributes (age, and colour).
           The first one can take one out of four different values
           and the second one of two values. This result in a network
           with 4*2=8 different edge states.

        meanFieldStates : list 
           A list of mean field states. The states specified in here will be 
           tracked by the process and stored as a `network` attribute.
           Each state is a dictionary made up of either node or edge 
           attribute:value pairs.
           
        runEdgeUpdate : bool
           See Process

        runNodeUpdate : bool
           See Process
        
        runNetworkUpdate : bool 
           See Process

        constantTopology : bool
           See Process

        """
        super(AttributeStateProcess, self).__init__(runNodeUpdate, runEdgeUpdate, runNetworkUpdate, 
                                                   constantTopology)

        self.nodeAttributeDict = nodeAttributeDict
#        logger.debug("Node attributes: {0}".format(nodeAttributeDict))
        self.edgeAttributeDict = edgeAttributeDict
        self.meanFieldStates = meanFieldStates

#        logger.debug("Mean field states: {0}".format(self.meanFieldStates))
        
        self.evalNS = {}

        for att,vals in nodeAttributeDict.iteritems():
            self.evalNS[att] = att
            self.evalNS.update(dict(zip(vals,vals)))

        for att,vals in edgeAttributeDict.iteritems():
            self.evalNS[att] = att
            self.evalNS.update(dict(zip(vals,vals)))

#        logger.debug("Constructed evalNS = {0}".format(self.evalNS))

    def initializeNetwork(self, network, *args, **kwargs):
        """
        Initialize the mean field states on the network.
        
        Parameters
        ----------
        
        network : networkx.Graph
           The network on which the process will run.
           
        Returns
        -------
        
        network : networkx.Graph
           `network` with updated attributes. Each additional attribute
           being a mean field state corresponding to the ones give in
           `meanFieldStates` when the object was initialized.

        See Also
        --------
           Process : Superclass

        """ 
        # Update the network with the number of nodes/edges in the tracked mean field states
        for s in self.meanFieldStates:
            sset = frozenset(s)
            network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME][sset] = networkxtra.entityCount(network.nodes_iter(data=True), sset)
        return network

    def initializeNetworkNodes(self, network, *args,**kwargs):
        """
        Set initial node states and parameters to a network.
        
        This implementation of initializeNetworkNodes assumes that it is passed
        the fraction/amount of nodes in each state as additional arguments.
        That is the parameter name must be a valid node state as declared 
        when the object is initialized and the value of the parameter must be
        an integer or a float. If all parameter values add up to the
        number of nodes in `network` the exact number of nodes in that state
        will be randomly distributed. If the sum is not the number of nodes the
        number of nodes in a particular state will be proportional to that number.

        Note
        ----

        State parameter names are strings on the form of python dictionaries.

        Parameters
        ----------

        network : networkx.Graph 
           The network to initialize

        kwargs : special
           One parameter name per state in the process model the value of which
           should be a number.

        Returns
        -------

        network : networkx.Graph
           The updated `network` object with node state distributed.

        See Also
        --------

        Process : Superclass

        """
        # All values should be floats, and the keys parse to dictionaries,
        # so let's convert them at this stage.

        # There may be a special parameter telling us if the nodes should 
        # be exactly distributed or scaled.
        dealExact = kwargs.pop(self.CFG_PARAM_deal_exact, 'no')
        
#        logger.debug(kwargs)
        nodeAtts = []
        for s,v in kwargs.iteritems():
            d = eval(s,self.evalNS)
            vf = float(v)
            nodeAtts.append((d,vf))

        # Distribute the states.
        networkxtra.attributeValueDeal(network.nodes_iter(data=True),
                                             nodeAtts, 
                                             network.number_of_nodes(),
                                             dealExact in ('yes', 'on', 'true'))
        return network

    def initializeNetworkEdges(self, network, *args, **kwargs):
        """
        Set initial edge states and parameters to a network.
        
        This implementation of initializeNetworkEdges assumes that it is passed
        the fraction/amount of edges in each state as additional arguments.
        That is the parameter name must be a valid node state as declared 
        when the object is initialized and the value of the parameter must be
        an integer or a float. If all parameter values add up to the
        number of nodes in `network` the exact number of nodes in that state
        will be randomly distributed. If the sum is not the number of nodes the
        number of nodes in a particular state will be proportional to that number.

        Note
        ----

        State parameter names are strings on the form of python dictionaries.

        Parameters
        ----------

        network : networkx.Graph 
           The network to initialize

        kwargs : special
           One parameter name per state in the process model the value of which
           should be a number.

        Returns
        -------

        network : networkx.Graph
           The updated `network` object with edge state distributed.

        See Also
        --------

        Process : Superclass

        """
        # There may be a special parameter telling us if the nodes should 
        # be exactly distributed or scaled.
        dealExact = kwargs.pop(self.CFG_PARAM_deal_exact, 'no')
        
        # All values should be floats, and the keys parse to dictionaries,
        # so let's convert them at this stage.
        edgeAtts = []
        for s,v in kwargs.iteritems():
            d = eval(s,self.evalNS)
            vf = float(v)
            edgeAtts.append((d,vf))

        # Distribute the states.
        networkxtra.attributeValueDeal(network.edges_iter(data=True),
                                             edgeAtts, 
                                             network.number_of_edges(),
                                             dealExact in ('yes', 'on', 'true'))
        return network

    def deduceNodeState(self, node):
        """
        Gives the state of a node.
        
        Will report a node state as the (frozen) set based on the node 
        attribute dictionary.
        
        Parameters
        ----------

        node : networkx node, Structure (<node id>, {<attribute name-value map>})
        
        Returns
        -------
        
        state : frozenset
           The state associated with `node`.
           
        See Also
        --------
        
        Process : Superclass

        """
        # This is an explicit state process, so we can just return it.
        return frozenset(node[-1].iteritems())
    
    def  deduceEdgeState(self, edge):
        """
        Gives the state of a edge.
        
        Will report a edge state as the (frozen) set based on the edge 
        attribute dictionary.
        
        Parameters
        ----------

        edge : networkx edge, Structure (<node id 1>, <node id 2>, <attribute dict>)
        
        Returns
        -------
        
        state : frozenset
           The state associated with `edge`.
           
        See Also
        --------
        
        Process : Superclass

        """
        # This is an explicit state process, so we can just return it.
        return frozenset(edge[-1].iteritems())


class ScriptedProcess(AttributeStateProcess):
    """
    A scripted process reads its node and edge rules, as well as states from a
    file.

    This allows for rapid prototyping of processes without the need of 
    overloading and implementing python classes. The state update rules are 
    written in an ini/python like script outlined below.

    None of the configuration sections in the ScriptedProcess ini file have 
    fixed options. Rather the option names and values are taken on specific
    forms to declare states and rules. This is explained in the table below 
    outlining the different sections and how to declare options in each:

    +-----------------+--------------------------------------------------------+
    | ScriptedProcess configuration sections                                   |
    +-----------------+--------------------------------------------------------+
    | Section         | Explanation                                            |
    +=================+========================================================+
    | NodeAttributes  | Declaration of node attributes.                        |
    |                 | Option names will be taken as attribute names, and the |
    |                 | value (a single value, or a comma-separated list) is a |
    |                 | list of all possible values this attribute can take.   |
    +-----------------+--------------------------------------------------------+
    | EdgeAttributes  | Declaration of edge attributes.                        |
    |                 | Option names will be taken as attribute names, and the |
    |                 | value (a single value, or a comma-separated list) is a |
    |                 | list of all possible values this attribute can take.   |
    +-----------------+--------------------------------------------------------+
    | MeanFieldStates | Declaration of mean field states.                      |
    |                 | Declaration of mean fields. This serves two purposes.  |
    |                 | First it allows the node and edge rules to access the  |
    |                 | fraction of nodes/edges in this state using the ``MF`` |
    |                 | operator (see below). Second, the number of            |
    |                 | nodes/edges in each mean field state will be given to  |
    |                 | simulation to be tracked over time. This field is not  |
    |                 | a standard ini-style option-value declaration. Rather  |
    |                 | only options (without the '=' sign) is allowed here.   |
    |                 | Each option is taken to be a declaration of a mean     |
    |                 | field state, and should be on dictionary form. I.e.    |
    |                 | ``{attribute1:key1, attribute2:key2, ...}``. Partial   |
    |                 | states are allowed here. Partial, meaning a dictionary |
    |                 | that either only specifies some of the states declared |
    |                 | in the NodeAttributes or EdgeAttributes sections, or   |
    |                 | which define their values on a form                    |
    |                 | ``{attribute_n:(key1, key2,..., key_m), ...}``.        |
    |                 | That is in the latter case, giving a tuple of          |
    |                 | alternative values for one or more attributes.         |
    |                 | In each of these cases a separate mean field state     |
    |                 | is created for every possible state being part of the  |
    |                 | state-sub-space defined by the partial state, and      |
    |                 | a special mean field state is created for the sub-     |
    |                 | space defined. It is also possible to use ``{}`` (the  |
    |                 | empty dictionary) to match every individual state,     |
    |                 | and the total mean field (constant).                   |
    +-----------------+--------------------------------------------------------+
    | NodeRules       | List of node transition rules.                         |
    |                 | Each option-value pair is considered a node update     |
    |                 | rule. The option is a string defining which node       |
    |                 | attribute set should match the rule, and if the rule   |
    |                 | is followed which attribute updates should be          |
    |                 | performed to the dictionary (thereby sending it to     |
    |                 | another state). The value is an expression computing   |
    |                 | the unit-time probability of following the rule.       |
    |                 | First let's give the option form. This is              |
    |                 | ``{attribute1:key1, attribute2:key2, ...} ->           |
    |                 | {attribute_k:key_k,...}``.                             |
    |                 | On the left side of the ``->`` sign is a full or       |
    |                 | partial state as a node attribute dictionary (see      |
    |                 | the mean field notes above) and will be matched to the |
    |                 | node state. If it is a partial state, rules for all    |
    |                 | possible states will be constructed. On the right side |
    |                 | of the ``->`` sign is the updates that should be       |
    |                 | performed to the dictionary in case the rule is        |
    |                 | followed through. Typically this is a change to a      |
    |                 | single attribute, but it is also possible to change    |
    |                 | multiple attributes. The option value is an expression |
    |                 | that should compute a probability in unit time. This   |
    |                 | is the probability that the rule is followed through   |
    |                 | and the update to the node dictionary is made. Any     |
    |                 | variable name used in this expression is assumed to be |
    |                 | a process parameter, and will have to be set in the    |
    |                 | simulation configuration. For variable names anything  |
    |                 | that is not a python specific names, or either `MF` or |
    |                 | ``NN``. The names ``MF`` and ``NN`` are specific       |
    |                 | functions that can  be used in the expression.         |
    |                 | ``NN({attribute1:key1, attribute2:key2, ...})``        |
    |                 | yields the number of nearest neighbors in the given    |
    |                 | state (or partial state).                              |
    |                 | There is also a special version that takes a second    |
    |                 | argument which should be a full or partial edge state. |
    |                 | The counting of nearest neighbors is then only         |
    |                 | performed on edges matching this edge state.           |
    |                 | ``MF({attribute1:key1, attribute2:key2, ...})``        |
    |                 | gives the mean field (fraction of nodes/edges) in the  |
    |                 | given state. Note that for ``MF`` only declared mean   |
    |                 | field states are valid. See the tutorial for examples. |
    |                 | Finally, several rules matching the same states can    |
    |                 | be written and they will be evaluated in the order     |
    |                 | declared.                                              |
    +-----------------+--------------------------------------------------------+

    Configuration File Sections
    ---------------------------
    
    The configuration file section names are given by the following class 
    attributes.

    CFG_SECTION_node_rules : string
       'NodeRules'
    
    CFG_SECTION_edge_rules : string
       'EdgeRules'

    CFG_SECTION_mean_field : string
       'MeanFieldStates'
    
    CFG_SECTION_node_attribs : string
       'NodeAttributes'

    CFG_SECTION_edge_attribs : string
       'EdgeAttributes'

       

    Examples
    --------
    
    *SIR process ini-file*
    The standard S-I-R model could be configured as follows::
       
       [NodeAttributes]
       # Declaration of node attributes and possible values.
       # A single attribute called state with three different possible values

       status = S,I,R
 
       [MeanFieldStates]
       # Declaration of mean filed states.
       # As no mean field states are used in the SIR calculations this section
       # could be left out. However, the Simulation will automatically log the
       # mean field states so it is convenient to declare the ones we want to
       # track.

       {status:S}
       {status:I}
       {status:R}

       [NodeRules]
       # Declaration of update rules.
       # Each rule is on the form <src state> -> <update> = <expression>
       # The states are given as python dictionaries. The expressions should
       # return the probability in unit time to execute the attribute update.
       # Special function 'NN' give the number of neighbors matching some
       # state dictionary. All undefined names are assumed to be parameters of
       # the process.x

       # From state S to state I: num. infected neighbors times a parameter beta.
       {status:S} -> {status:I} = NN({status:I}) * beta

       # From state I to state R: a flat rate gamma.
       {status:I} -> {status:R} = gamma

    
       
    """

    # The sections in the ini file given to the class.
    CFG_SECTION_node_rules = "NodeRules"
    CFG_SECTION_edge_rules = "EdgeRules"
    CFG_SECTION_mean_field = "MeanFieldStates"
    CFG_SECTION_node_attribs = "NodeAttributes"
    CFG_SECTION_edge_attribs = "EdgeAttributes"
    # This is the expected key in the arguments sent to the
    # __init__ function.
    CFG_PARAM_config_file = "file"

    

    def __init__(self, **kwargs):
        """
        Reads process configuration from file and initializes process.
        
        If no node/edge rules are given the corresponding update functionality
        is turned off in Superclass `Process`.
        
        Parameters
        ----------

        file : string
           The name and path of the configuration file.

        kwargs : special
           All additional parameters passed to __init__ will be treated
           as being process rule parameters and will be added to the rule
           evaluation namespace.

        Note
        ----
        
        Currently constant topology is assumed.

        Currently *only* node updates are performed even if
        edge rules are given!!

        """
        if not kwargs.has_key(self.CFG_PARAM_config_file):
            err = "No config file given for ScriptedProcess!"
            logger.error(err)
            raise(NepidemiXBaseException(err))

        # Get the config File from the arguments
        configFileName = kwargs[self.CFG_PARAM_config_file]
        # Use all parameters except the file name as
        # model parameters. Convert them to float.
        self.modelParameters = {}
        for key,val in kwargs.iteritems():
            if key != self.CFG_PARAM_config_file:
                self.modelParameters[key] = float(val)
#        logger.debug("Process parameters given: {0}"\
#                         .format(self.modelParameters))

        creader = nepx.utilities.NepidemiXConfigParser()
        try:
            with open(configFileName, 'r') as fp:
                creader.readfp(fp)
        except IOError as (errno, strerror):
            logger.error("Could not open process config file : '{0}'"
                         .format(configFileName))

        # These are the 'protected' names (of operators).
        protNames = set(['NN', 'MF'])
        
        
        nodeAtts = dict([(att, creader.parseTuple(vals)) for att, vals in creader.items(self.CFG_SECTION_node_attribs)])
        edgeAtts = dict([(att, creader.parseTuple(vals)) for att, vals in creader.items(self.CFG_SECTION_edge_attribs)])

        # Temporarily set mean field states to the list of strings.
        meanFieldStates = [ att for att, val in creader.items(self.CFG_SECTION_mean_field)]

        nodeRuleList = creader.items(self.CFG_SECTION_node_rules)
        edgeRuleList = creader.items(self.CFG_SECTION_edge_rules)

        super(ScriptedProcess, self).\
            __init__(nodeAtts,
                     edgeAtts,
                     meanFieldStates,
                     runNodeUpdate = (len(nodeRuleList) > 0),
                     runEdgeUpdate = (len(edgeRuleList) > 0),
                     runNetworkUpdate = False,
                     constantTopology = True)
        
        # Create rule mappings.
        self.nodeRules = self._createRuleDict([(creader.parseMapping(s),r) for s,r in nodeRuleList], self.nodeAttributeDict)
        self.edgeRules = self._createRuleDict([(creader.parseMapping(s),r) for s,r in edgeRuleList], self.edgeAttributeDict)

        # Add the functions to the namespace dictionary.
        self.evalNS['NN'] = self._NNlookup
        self.evalNS['MF'] = self._MFlookup

        # Add the parameters.
        self.evalNS.update(self.modelParameters)
#        logger.info("Found rules: {0}".format(self.nodeRules))
#        logger.debug("Found node rule source states: {0}".format(self.nodeRules.keys()))


    def initializeNetwork(self, network, *args, **kwargs):
        """
        Initialize the mean field states on the network.
        
        This is a specialized version of initializeNetwork as found in 
        `AttributeStateProcess` and allows for partial mean field states.
        In a partial state only a subset of the declared state keys are defined
        thus the partial state matches many unique states. This method will
        deduce all unique states lying in the partial state and track each of them.
        Thus if you want every possible state to be tracked as a mean field an
        empty dictionary '{}' can be given which will match all possible states.
        
        Parameters
        ----------
        
        network : networkx.Graph
           The network on which the process will run.
        
        Returns
        -------
        
        network : networkx.Graph
           `network` with updated attributes. Each additional attribute
           being a mean field state corresponding to the ones give in
           `meanFieldStates` when the object was initialized.
        
        See Also
        --------
           Process : Superclass
        
        """ 
        # Need to overload this as the mean fields can be partial states.
        # Work over the meanField states to evaluate keys and to separate them into
        # the different possible states.
        nmfl = []
        for s in self.meanFieldStates:
            
            res = eval(s, self.evalNS)
            oStateSet, allsets  = self._createAllPossibleSets(res, self.nodeAttributeDict)
            # List for linked counters
            nsum = 0
            l = []
            if not network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME].has_key(oStateSet):
                if len(allsets) > 1:
                    # If multiple target states were created, we need to create a listener
                    # for the generalized mean field state.
                    listnr = LinkedCounter(nsum)
                    l.append(listnr)
                    network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME][oStateSet] = listnr
                for k in allsets:
                    # Count number of nodes matching this state.
                    nns = networkxtra.entityCountSet(network.nodes_iter(data=True), k)
                    # Add them to the network graph.
                    if network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME].has_key(k):
                        network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME][k].linkedCounters.extend(l)
#                        logger.debug("Leaf state {0} LINKED to partial state(s) {1}".format(k,l))
                    else:
                        network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME][k] = LinkedCounter(nns, l)
#                        logger.debug("Leaf state {0} CREATED. Initial count: {1}".format(k,nns))
                # If we created a listener we need to set is value to the sum as well.
                if len(allsets) >1:
                    osnns = networkxtra.entityCountSet(network.nodes_iter(data=True), oStateSet)
                    network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME][oStateSet].counter = osnns 
#                    logger.debug("Partial state {0} CREATED, inital value set to {1}".format(oStateSet, osnns))

            # Extend sets.
            nmfl.extend(allsets)


        self.meanFieldStates = nmfl

        self._currentMeanField = network.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME]
        # As we have constant topology.
        self._currentNetworkSize = float(network.number_of_nodes())


        return network



    def _createRuleDict(self, ruleList, referenceDict):
        """
        Given a set of rules as strings this method create a list of 
        dictionaries on with key value pairs as
        source_state_set : (state_update_dict, code_object)
        Source state set is a set representing a node or edge state. 
        Stat update dict is a dictionary with the attribute value(s) to update
        in case the rule is followed. 
        Code object is a compiled version of the code.

        Parameters
        ----------

        ruleList : list
           A list of tuples ((source state string, dest state string), rule string)
        referenceDict : dict 
           Dictionary of allowed attribute names and tuples of their allowed values.
        
        Returns
        -------
        
        trules : orderedDict
           A list of dictionaries keyed by source state set.
        
        """
        # Store rules as a dictionary of lists.
        # The key is the source state and each item in the list is
        # a pair (destination state, rule as string)
        tmpRules = collections.OrderedDict()
        # Read rules.
        for mpair,rule in ruleList:
            # Extract states.
            
            fromState = eval(mpair[0], self.evalNS)
            # Get all possible matching states.
            oStateSet, fromStateList = self._createAllPossibleSets(fromState, referenceDict)
            toState = eval(mpair[1], self.evalNS)
            # Create rule-code.
            rCode = compile(rule,"<string: '{0}'>".format(rule),mode='eval')
            for fst in fromStateList:
                # The dictionary has source state as key, and the value is a pair where
                # first value is the target state, and the second value is a compiled code object.
                if not tmpRules.has_key(fst):
                    tmpRules[fst] = []
                tmpRules[fst].append((toState, rCode))

        return tmpRules

    def _createAllPossibleSets(self, attDict, referenceDict):
        """
        From an attribute dictionary that may or may not be a full
        state, create all possible full states as a list of dictionaries.
        
        The attribute dictionary can be a full state (having a single value for all attributes),
        or multiple states (having multiple values for the same attribute) or even be a
        partial state (lacking attributes). All possible states reached by further specializing
        the dictionary is returned.
        
        Parameters
        ----------
        
        attDict : dict
           Dictionary where the keys are node/edge attribute names and
           the value is a tuple of attribute values or a single value.
        referenceDict :dict
           Dictionary of all valid attributes and their allowed values.

        Returns
        -------

        stlist : dict
           List of dictionaries. Each dictionary is a possible state reached from attDict.
        
        """
        stlist = [{}]
        oset = frozenset(attDict.iteritems())
        for a,op in referenceDict.iteritems():
            if not attDict.has_key(a):
                attDict[a] = op
            if not type(attDict[a]) == tuple:
                attDict[a] = (attDict[a],)

            # For every additional attribute create a new copy of the full list.
            stlexten = []

            for c in attDict[a]:
                # For each additional attribute.
                # Copy the original list.
                tmplist = copy.deepcopy(stlist)
                # Set the attribute value to the current.
                for d in tmplist:
                    d[a] = c
                # Extend the list.
                stlexten.extend(tmplist)
            # When we are done update the list for this attribute.
            stlist = stlexten
        # Return sets of the dictionaries.
#        logger.debug("Computed list of possible states: {0}".format(stlist))
        return (oset, [frozenset(d.iteritems()) for d in stlist])
            
            
                    
    
    def nodeUpdateRule(self, node, srcNetwork, dt):
        """
        Perform local node changes.
     
        When called by Simulation this method will execute the matching rules 
        for the current node in the same order they were given in the 
        configuration file and, by some probability, follow it through; 
        making changes to its state accordingly. 
        As soon as one rule is matched the state is updated and no further 
        rules are tested.
        If no rules matched of were triggered then the state remains unchanged.

        Parameters
        ----------
        
        node : networkx node, Structure: (<node id>, {<attribute name-value map>})
           This is a copy of the current node and the target of any changes.
           
        srcNetwork : networkx.Graph
           A networkX graph, with the original nodes. Will remain unchanged.
        
        dt : float
           Time differential (float) as a fraction of time unit (since last 
           update).
        
        Returns
        -------

        node : networkx node
           `node` with changes

        See Also
        --------
        
        Process : Superclass

        """
        # For the sake of MF make sure that _currentMeanField always points
        # to the current srcNetwork.graph.
        self._currentMeanField = srcNetwork.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME]

        # Create a nearest neighbor generaterator.
        self._currentNNIter = [ n for n in networkxtra.neighbors_data_iter(srcNetwork, node[0])]
        # And the nearest adj matrix.
        self._currentAdj = srcNetwork.adj[node[0]]
        # Create random event.
        eventp = numpy.random.random_sample()
        
        # As we may check a number of possible destination
        # states the probability of each sequential one
        # must be going up given that we did not go into
        # the previous one. This is the accumulated probab.
        # that we test the event against.
        prob = 0
        # Evaluate go over the edges in the rule graph.
        # Linear lookup of the rules.
        # First look up a matching rule. Most general match first.
        done = False
        rList = self.nodeRules.get(frozenset(node[-1].iteritems()), [])
#        logger.debug("Trying rules: {0} from state: {1}".format(rList, node[-1]))
        for dSt, rule in rList:
            # Update probability by the evaluated rule code object.
            prob += eval(rule, self.evalNS) * dt 
            # Check if this is the event that is happening.
            if eventp < prob:
                node[-1].update(dSt)
                break
        return node

    def _NNlookup(self, nodeAtts, givenEdgeAtts = None):
        """
        Internal function that is mapped to the symbol 'NN' for use in the process definition
        string. Thus
        NN(dict) gives the number of nearest neighbors of the current node that has the attributes
        described by the dictionary dict.
        The special case NN(ndict, edict) gives the number of nearest neighbors with
        attribute values specified in ndict, that is connected on an edge with edge
        attributes set to those in edict.

        Parameters
        ----------

        nodeAtts : dict
           Node state dictionary matching a specific or partial state.

        givenEdgeAtts : dict, optional
           If not None this should be a dictionary of edge attributes matching
           either a specific or partial state. The nearest neighbors will in 
           that case only be counted over edges with attributes matching that 
           particular dictionary.

        Returns
        -------

        nnodes : int
           Number of nearest neighbors matching a particular state dictionary.
        
        """
        if givenEdgeAtts == None:
            return networkxtra.entityCountDict(self._currentNNIter, nodeAtts)
        else:
            r =  networkxtra.entityCountDict([n for n in self._currentNNIter if networkxtra.matchDictAttributes(self._currentAdj[n[0]], givenEdgeAtts)], nodeAtts)

            return r
        

    def _MFlookup(self, atts):
        """
        Internal function that is mapped to the symbol 'MF' for use in the process definition
        string. MF(dict) give the mean field of nodes on the network in state (if a partial state
        is given the mean field of all nodes matching this is returned) dict. Note that the mean
        field must be know, i.e. declared in the process definition to be used here.

        Parameters
        ----------

        atts : dict
           Attribute dictionary matching a specific or partial mean field state.

        """
        rv = self._currentMeanField[frozenset(atts.iteritems())] / self._currentNetworkSize
        return rv

    
class ScriptedTimedProcess(ScriptedProcess):
    """
    A ScriptedTimedProcess behaves like a `ScriptedProcess` but time spent in 
    specific states can be queried.

    This process is configured just like `ScriptedProcess`, however it records 
    the global time of value changes to the state space attributes, and give 
    access to these through the function T0(...) and T(...).

    - T0( state ) gives the time stamp when the state happened. 'state' should
      be given on the standard dictionary form and be either a full or partial 
      state. It will give the point closest in time (the maximum) when the
      specified attributes got the specified key values.

    - T( state ) gives the time the node has spent in the specified state.
      'state' should be given on the standard dictionary form and be either a 
      full or partial state. This function will give the shortest time any of
      the specified attributes has spent in their corresponding key state.

    Note that as such these functions do not return an error if you happen to
    ask for time for a state that the node is not in (or that does not exist), 
    it simply gives you a time of zero spent in the state (or the current time 
    stamp for T0(...) ).

    Examples
    --------

    *Weibull distributed failure rate*
    Assume you have the attribute 'working' that can take on the values of
    'yes' or 'no'. A Weibull distributed failure rate would be encoded as
    
       {working : yes} -> {working : no} = k/l * (T({status:yes}) / l) ** (k-1.0)

    where k,l are parameters (shape and scale), T({status:yes}) gives the time
    with the 'working' attribute set to 'yes'. Note that as this rule is valid
    for nodes in this state, we know that T will always return a sensible value.
    The operator '**' is the power operator.

    """
    def __init__(self, **kwargs):
        """
        Reads process configuration from file and initializes process.
        
        See Also
        --------
        ScriptedProcess : Superclass
        """
        super(ScriptedTimedProcess, self).__init__(**kwargs)
        self.evalNS['T0'] = self._T0
        self.evalNS['T'] = self._T
        self._currentTime = None
        self._currentState = None

    def initializeNetwork(self, network, *args, **kwargs):
        """
        Initialize the mean field states on the network.
        
        See Also
        --------
        ScriptedProcess : Superclass
        """

        # Use the parent class method
        netw = super(ScriptedTimedProcess, self).initializeNetwork(network, *args, **kwargs)
        # If there are no time stamps, create them and set all to current network time.
        
        # Nodes
        if len(self.nodeRules) > 0:
            self._mapToTSS(network.nodes_iter(data=True), network.graph[nepx.Simulation.TIME_FIELD_NAME])

        if len(self.edgeRules) > 0:
            self._mapToTSS(network.edges_iter(data=True), network.graph[nepx.Simulation.TIME_FIELD_NAME])

    def nodeUpdateRule(self, node, srcNetwork, dt):
        """
        Perform local node changes.
     
        When called by Simulation this method will execute the matching rules 
        for the current node in the same order they were given in the 
        configuration file and, by some probability, follow it through; 
        making changes to its state accordingly. 
        As soon as one rule is matched the state is updated and no further 
        rules are tested.
        If no rules matched of were triggered then the state remains unchanged.

        Parameters
        ----------
        
        node : networkx node, Structure: (<node id>, {<attribute name-value map>})
           This is a copy of the current node and the target of any changes.
           
        srcNetwork : networkx.Graph
           A networkX graph, with the original nodes. Will remain unchanged.
        
        dt : float
           Time differential (float) as a fraction of time unit (since last 
           update).
        
        Returns
        -------

        node : networkx node
           `node` with changes

        See Also
        --------
        ScriptedProcess : Superclass
        Process : Superclass
        
        """
    
        # This re-implements a lot of the functionality in ScriptedProcess::nodeUpdateRule which is a bit
        # of a shame.

        # For the sake of MF make sure that _currentMeanField always points
        # to the current srcNetwork.graph.
        self._currentMeanField = srcNetwork.graph[nepx.simulation.Simulation.STATE_COUNT_FIELD_NAME]
        

        # Grab current time, the network is from the previous iteration
        self._currentTime = srcNetwork.graph[nepx.Simulation.TIME_FIELD_NAME]
        # Take current node state
        self._currentState = node[-1]
        # Create a nearest neighbor generaterator.
        self._currentNNIter = [ n for n in networkxtra.neighbors_data_iter(srcNetwork, node[0])]
        

        # And the nearest adj matrix.
        self._currentAdj = srcNetwork.adj[node[0]]
        # Create random event.
        eventp = numpy.random.random_sample()
        
        # As we may check a number of possible destination
        # states the probability of each sequential one
        # must be going up given that we did not go into
        # the previous one. This is the accumulated probab.
        # that we test the event against.
        prob = 0
        # Evaluate go over the edges in the rule graph.
        # Linear lookup of the rules.
        # First look up a matching rule. Most general match first.
        done = False
        rList = self.nodeRules.get(frozenset(node[-1].iteritems()), [])
        for dSt, rule in rList:
            # Update probability by the evaluated rule code object.
            prob += eval(rule, self.evalNS) * dt 
            # Check if this is the event that is happening.
            if eventp < prob:
                node[-1].update(dSt)
                # Note that a self-loop rule here will lead to a reset of that
                # attribute timer.
                for chAtt in dSt.keys():
                    node[-1][chAtt] = _TimedState(node[-1][chAtt], 
                                                  self._currentTime
                                                  )
                break
        return node

    def _mapToTSS(self,featureIterator, time):
        """
        Map attribute keys from str to `_TimedState` objects.
        
        Go though all nodes/edges pointed to by featureIterator and
        (if the attribute values are strings) set them to _TimedState
        objects with time 'time'.

        Parameters
        ----------
        
        featureIterator : iterator
           Node or Edge iterator.

        time : float
           Time to initialize new _TimedState objects to.

        """
        for feature in featureIterator:
            for k in feature[-1].keys():
                if type(feature[-1][k]) is str and \
                        not hasattr(feature[-1][k], "attrTimeStamp"):
                    feature[-1][k] = _TimedState(feature[-1][k], time)

    def _T0(self, atts):
        """
        Compute the time stamp closest in time that the node/edge has spent in
        the given state, or the current time if the node/edge is not in the 
        specified state.

        Parameters
        ----------

        atts : dictionary
           attrbute - value pairs of the requested state

        Returns
        -------

        The greatest time stamp of the (partial) state
        """
        return numpy.max([self._currentState[k].time \
                              if self._currentState[k] == atts[k] \
                              else self._currentTime \
                              for k in iter(atts)])

    def _T(self, atts):
        """
        Compute the time spent in the specified (partial) state.

        Parameters
        ----------
        
        atts : dictionary
           Attribute - value pairs of the requested state

        Returns
        -------

        The shortest time spent in the state given state combination, or 0 if
        the node/edge is not in this state.
        """
        return self._currentTime - self._T0(atts)

# Inherit from str, add a time field as a meta field.
# Not very pretty.
class _TimedState(object):
    """
    These are timed string attributes as used by `ScriptedTimedProcess`.
    
    Basically treated as a string for all purposes except that it also has
    a time state.

    Note: Ought to be nested inside `ScriptedTimedProcess` but this causes
    problems with pickling so right now defined as a protected class at
    the module level.
    """
    def __init__(self, value, time):
        self.value = value
        self.time = time
    
    def __hash__(self):
        return self.value.__hash__()

    def __eq__(self, other):
        if type(other) is type(self):
            other = self.value
        return self.value.__eq__(other)

    def __le__(self, other):
        if type(other) is type(self):
            other = self.value
        return self.value.__eq__(other)

    def __lt__(self, other):
        if type(other) is type(self):
            other = self.value
        return self.value.__lt__(other)

    def __ne__(self, other):
        if type(other) is type(self):
            other = self.value
        return self.value.__ne__(other)

    def __gt__(self, other):
        if type(other) is type(self):
            other = self.value
        return self.value.__gt__(other)

    def __ge__(self, other):
        if type(other) is type(self):
            other = self.value
        return self.value.__ge__(other)

    def __repr__(self):
        return self.value.__repr__()

    def __str__(self):
        return self.value.__str__()

    def __cmp__(self, other):
        if type(other) is type(self):
            other = self.value
        return self.value.__cmp__(other)


