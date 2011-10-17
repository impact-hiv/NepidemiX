"""
=========
NepidemiX
=========

Provides a python interface to the NepidemiX network simulation.

NepidemiX - simulation of contact processes on networks.

NeipdemiX is a Python software package for running complex process
simulations on networkx graphs. A Simulation consists of a network (graph) and a Process that updates the state of the network entities (nodes and edges).

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

__all__ = []

import nepidemixlogging

import exceptions

import utilities

import process
from process import *

import simulation
from simulation import *

import cluster

import version

__all__.extend(process.__all__)
__all__.extend(simulation.__all__)
__all__.append('networkgeneratorwrappers')
