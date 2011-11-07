=============
API reference
=============

The NepidemiX package provides a configurable Simulations class, and a 
hierarchy of Process classes. The most common way of using NepidemiX would be
through scripts, however in some special cases, such as when the process 
configuration language is not powerful enough, python programming may be the
best solution.

This reference documents the most common NepidemiX classes and utilities.

.. _API_Simulations:

Simulations
===========
.. currentmodule:: nepidemix

.. automodule:: nepidemix.simulation

.. currentmodule:: nepidemix.simulation

.. autosummary::
   :toctree: _generated

   Simulation


.. _API_Processes:

Processes
=========
.. currentmodule:: nepidemix

.. automodule:: nepidemix.process

.. currentmodule:: nepidemix.process

.. autosummary::
   :toctree: _generated

   Process
   AttributeStateProcess
   ExplicitStateProcess
   ScriptedProcess

.. _API_Utilities:   

Utilities: nepidemix.utilities
==============================

Aside from the main classes, nepidemix has a many support functions and classes. The ones directly related to the configuring and running simulations are outlined below.

.. currentmodule:: nepidemix.utilities

.. automodule:: nepidemix.utilities.nepidemixconfigparser


.. autosummary::
   :toctree: _generated

   NepidemiXConfigParser

.. automodule:: nepidemix.utilities.networkgeneratorwrappers

.. autosummary::
   :toctree: _generated

   NetworkGenerator


.. currentmodule:: nepidemix.utilities.networkxtra

.. automodule:: nepidemix.utilities.networkxtra

.. autosummary::
   :toctree: _generated
   
   neighbors_data_iter
   attributeCount
   attributeValueDeal
   loadNetwork

NetworkX graph generators
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: _generated

   albert_barabasi_physrevlett_quick
   albert_barabasi_physrevlett_rigid
   powerlaw_degree_sequence

   
