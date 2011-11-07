
=============
Documentation
=============


Introduction 
==============

There are two ways to use NepidemiX: through a configurable command line program or by writing your won Python programs accesin the NepidemiX classes. 
Simulations and processes can be 
specified in a simple configuration file and can be extended using Python or both.

If you are new to NepidemiX it is recommended that you start with the 
:ref:`tutorial`. which shows both how to script simulations using config files and howt to write them as Python classes.

This page is intended as a very brief documentation outlining some of the features of the NepidemiX package, higlighting some of the features introduced by the tutorial. It lists the different configuration and scripting options, and link to the documentation for the main classes used for programming. A full API documentation is best accessed through the Pyhthon docstrings as shown in the :ref:`tutorial`.



Simulations, processes and networks 
===================================


At the core of NepidemiX is the :ref:`Simulation <NepidemiX-API-Simulation>` class. This is basically an engine that iterates through a given number of time steps and for each executes some functionality determined by a process on a network. It encapsulates the logic independent of network structure or process functionality. Thus, a simulation takes require a specialized process, as well as a given network to function.

As nepidemix was intended to mainly run simulations and these can be rather complex as well as dependent on the type of process and network used, the Simulation class is initialized using a configuration object. Currently this is a :ref:`Nepidemix-API-NepidemixConfigParser` object, derived from the python2 standard class ConfigParser.RawConfigParser, but this may come to change in future versions. The configuration will among other things tell the simulation class what type of process to use and what kind of network generating function. Simulation will thereafter create both these objects.

API-reference: :ref:`API_Simulations`


Network generation 
-------------------

There is no dedicated network class in networkmodule, instead it relies on the very well developed and efficient `NetworkX <http://networkx.lanl.gov/>`_ Graph. 
In order to tell Simulation what graph to generate the configuration option **network_func** is set. However, this can not be set directly to a NetworkX Graph generating function. Instead it must be set to a so called wrapper that takes the options destined for the function (as given in the section **NetworkParameters**) and cast them to the appropriate types. This is due to the fact that there is no native way of determine either type from a raw ini file, nor to query a python function for what types it requires for its parameters.

The current solution is not very elegant, a future update of the software will include type specification possibilities in the ini file instead. Currently, however, wrappers are defined in the nepidemix file networkgenerationwrappers.py . One example is::
   
   grid_2d_graph_networkx = NetworkGenerator(networkx.grid_2d_graph,{'m':int, 'n':int}).create

Note the .create at the end. 
This line creates a wrapper for the networkx function grid_2d_graph. NetworkGenerator is a class defined in networkgenerationwrappers. As first argument it takes the name of a function, and as second a dictionary mapping between said functions parameter names and python types. networkx.grid_2d_graph takes two parameters m and n, both integers.
After this is done we can set::

   network_func = grid_2d_graph_networkx

in the config file, and also use **m** and **n** as options in the **NetworkParameters** section.

Thus if you write your own network generator you will need to first write the function and then also wrap it as shown above.

Hopefully you will not have to; wrapper for common functions exist already as given in the table below.

+-----------------------------------------+--------------------+--------------------------------------------------------------------+
| Wrapper name                            | Parameter, type    | Description reference                                              |
+=========================================+====================+====================================================================+
| barabasi_albert_graph_networkx          | - **n**, int       | `NetworkX barabasi_albert_graph`_                                  |
|                                         | - **m**, int       |                                                                    |
+-----------------------------------------+--------------------+--------------------------------------------------------------------+
| albert_barabasi_prv_quick               | - **N**, int       | :ref:`NepidemiX-API-networkxtra.albert_barabasi_physrevlett_quick` |
|                                         | - **m**, int       |                                                                    |
|                                         | - **p**, float     |                                                                    |
|                                         | - **q**, float     |                                                                    |
+-----------------------------------------+--------------------+--------------------------------------------------------------------+
| connected_watts_strogatz_graph_networkx | - **n**, int       | `NetworkX connected_watts_strogatz_graph`_                         |
|                                         | - **k**, int       |                                                                    |
|                                         | - **p**, float     |                                                                    |
+-----------------------------------------+--------------------+--------------------------------------------------------------------+
| powerlaw_cluster_graph_networkx         | - **n**, int       | `NetworkX powerlaw_cluster_graph`_                                 |
|                                         | - **m**, int       |                                                                    |
|                                         | - **p**, float     |                                                                    |
+-----------------------------------------+--------------------+--------------------------------------------------------------------+
| powerlaw_degree_sequence                | - **n**, int       | :ref:`NepidemiX-API-networkxtra.powerlaw_degree_sequence`          |
|                                         | - **a**, float     |                                                                    |
+-----------------------------------------+--------------------+--------------------------------------------------------------------+
| grid_2d_graph_networkx                  | - **m**, int       | `NetworkX grid_2d_graph`_                                          |
|                                         | - **n**, int       |                                                                    |
+-----------------------------------------+--------------------+--------------------------------------------------------------------+
| fast_gnp_random_graph_networkx          | - **n**, int       | `NetworkX fast_gnp_random_graph`_                                  |
|                                         | - **k**, int       |                                                                    |
|                                         | - **p**, float     |                                                                    |
+-----------------------------------------+--------------------+--------------------------------------------------------------------+
| load_network                            | - **file**, str    | :ref:`NepidemiX-API-networkxtra.loadNetwork`                       |
+-----------------------------------------+--------------------+--------------------------------------------------------------------+


.. _`NetworkX barabasi_albert_graph`: http://networkx.lanl.gov/reference/generated/networkx.generators.random_graphs.barabasi_albert_graph.html#networkx.generators.random_graphs.barabasi_albert_graph

.. _`NetworkX connected_watts_strogatz_graph`: http://networkx.lanl.gov/reference/generated/networkx.generators.random_graphs.connected_watts_strogatz_graph.html#networkx.generators.random_graphs.connected_watts_strogatz_graph

.. _`NetworkX powerlaw_cluster_graph`: http://networkx.lanl.gov/reference/generated/networkx.generators.random_graphs.powerlaw_cluster_graph.html#networkx.generators.random_graphs.powerlaw_cluster_graph

.. _`NetworkX grid_2d_graph`: http://networkx.lanl.gov/reference/generated/networkx.generators.classic.grid_2d_graph.html#networkx.generators.classic.grid_2d_graph

.. _`NetworkX fast_gnp_random_graph`: http://networkx.lanl.gov/reference/generated/networkx.generators.random_graphs.fast_gnp_random_graph.html#networkx.generators.random_graphs.fast_gnp_random_graph


The Process class 
==================

A process is a set of operations executing on a network each iteration of the simulation. The Simulation class will call methods in a process object representing different stages such as node and edge state updates, network state initialization, et c. Processes are subclasses of the class :ref:`networkmodule.process.Process <NepidemiX-API-Process>`. This class defines the interface for all processes, and by overloading the methods of this class different specific processes functionality is created. networkmodule.process also contain a few ready defined processes such as the generic ScriptedProcess.

Processes operate at network/edge level as well as network level. The node and edge updates look at one entity at a time, but have access to read from the full network. The network update is called for the entire network and can operate on that level. As most processes we are interested in are on the form `if node/edge state is x then with some probability move it into state y`. Such rules will only write to a single entity (node/edge) at a time and can be fully implemented using local (per-entity) update rules only. The whole network update can later be used if other data/updates are needed, for instance mean field or topology changes.

What is then a *state* which the rules change? From the view of NepidemiX it is up to the programmer to decide, but must be deduced from a single NetworkX entity (node/edge). Thus in the case of a NetworkX node the update rule cab be triggered by the node ID (usually an integer, but could be anything NetworkX can use) and the associated dictionary - which of course can be any combination of (hash-able) key-attribute values. Thus the 'true' state of the node is the information of the node. By convention however, it is usually more practical to consider the state to be defined by the node attributes, or a subset thereof. 

For this reason there are two main subclasses of :ref:`NepidemiX-API-Process`: :ref:`NepidemiX-API-ExplicitStateProcess`, and :ref:`NepidemiX-API-AttributeStateProcess`. The first assumes names are given to each possible state that a node/edge can be in. For instance in an SIR-model, the nodes can be in one of three states: **S**, **I**, or **R**. In practice, only a single attribute (naming the state) is associated with each node. While practical for a large class of models, there are times when the number of individual states are so large that explicit enumeration may be prohibiting. In these cases the class :ref:`NepidemiX-API-AttributeStateProcess` may be used instead. This specialization of :ref:`NepidemiX-API-Process` assume instead that the state is a combination of node/edge attributes. The full node attribute dictionary, or a subset thereof. 

When talking about processes derived from :ref:`NepidemiX-API-AttributeStateProcess` they all have states in the form of a dictionary (you can think of this as a vector, only with named elements instead of ordered). In this documentation, and in code, we denote the states by a dictionary in python form. E.g. *{key1:attribute1, key2:attribute2, ...}*.


For practical examples see :ref:`tutorial`.

API-refrence: :ref:`API_Processes`

The following sections and options are available to a stand alone simulation.



Cluster options
===============


When processing a configuration through the cluster module all stand alone option values (listed above) are allowed to be expressed as lists or ranges.
The format of a list is comma-separated
**<option> = <value 1>, <value 2>, ..., <value n>**
while a range must have the following form **<option> = <start> : <step> : <end>** and will produce a list from <start> (inclusive) to <end> (exclusive) with step size <step>.

Examples::

   # This range will produce the value 100, 150, 200 for n.
   n = 100:50:200
   # This is a list of different values of p.
   p = 0.1, 0.24, 0.51, 0.79


In addition the following sections and options are available for configuring the cluster module.



ScriptedProcess options 
------------------------

If you use the **ScriptedProcess** class it will take a rule definition file as input. This is an ini-type file with the following sections and options.


For examples on how to use ScriptedProcess see [[NepidemiX (Tutorial)]].
