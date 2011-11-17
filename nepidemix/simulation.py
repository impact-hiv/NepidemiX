"""
=======================
Network simulation core
=======================

This module contains the main Simulation class.

A simulation object is responsible for creating network and process and to 
execute the main loop, running the process on the network. It also handles I/O
and logging. Saving data after each run.

"""

__author__ =  "Lukas Ahrenberg (lukas@ahrenberg.se)"

__license__ = "Modified BSD License"

__all__  = ['Simulation']

import numpy
import sys
import imp
import csv
import time
import networkx
import copy
import os
import collections

# Local imports

from nepidemix import process


from nepidemix.exceptions import NepidemiXBaseException

from nepidemix.utilities import NepidemiXConfigParser

# Logging
import logging

# Set up Logging
logger = logging.getLogger(__name__)


class Simulation(object):
    """
    Captures the functionality of a simulation in a class.

    A simulation has three stages: configuration, execution, and data export.
    Configuration is made using an ini-like language, and the configure method
    takes a Python ConfigParser compatible structure.
    Once the simulation is configured it is started by execute, and finally call
    saveData in order to save any simulation data to disc.
    
    What data is saved depends on how the simulation is configured (as outlined
    below) and on which process is used. Currently the simulation can be set up
    to track the number of nodes in each mean field state defined by the process
    and/or the full network (topology and states).

    A very short example running a simulation (given a configuration file named
    'myconfig.ini'::
       
       cfParser = nepidemix.utilities.NepidemiXConfigParser()

       configFileName = 'myconfig.ini'

       with open(configFileName) as f:
               cfParser.readfp(f)

       S = nepidemix.simulation.Simulation()

       S.configure(cfParser)

       S.execute()

       S.saveData()
    

    Configuration files are written in an ini-like language with sections and
    <option> = <value> pairs in each. The Section and Option names are given by
    the CFG-prefixed attributes of the Simulation class.

    The following table contains explanations of all valid ini-file configuration sections.

    +-----------------------+------------------------------------------------+
    |                    List of configuration sections                      |
    +-----------------------+------------------------------------------------+
    |        Section        |                  Explanation                   |
    +=======================+================================================+
    | Simulation            | This section contains general simulation       |
    |                       | information such as what network generation    |
    |                       | and process to use.                            |
    |                       | See table of Simulation section options below  |
    |                       | for specific settings.                         |
    +-----------------------+------------------------------------------------+
    | NetworkParameters     | This is a special section. All options will be |
    |                       | sent as parameters to the network generation   |
    |                       | function (set by the ``network_func`` option   |
    |                       | in the ``Simulation`` section). Thus the       |
    |                       | options in this section is dependent on the    |
    |                       | function chosen, and must match that function  |
    |                       | exactly. See                                   |
    |                       |``nepidemix.utilities.networkgeneratorwrappers``|
    |                       | for a list of network generation functions.    |
    +-----------------------+------------------------------------------------+
    | ProcessParameters     | This is a special section. All options will be |
    |                       | sent as parameters to the process class (set   |
    |                       | by the ``process_class`` option in the         |
    |                       | ``Simulation`` section) initialization method. |
    |                       | Thus the options in this section is dependent  |
    |                       | on the process chosen, and must match that     |
    |                       | class exactly. See nepidemix.Process for a     |
    |                       | brief introduction, and the tutorial for       |
    |                       | examples.                                      |
    +-----------------------+------------------------------------------------+
    | NodeStateDistribution | This is a special section. The section will be |
    |                       | ignored if ``network_init`` is turned off. All |
    |                       | options will be sent as parameters to the      |
    |                       | process class (set by the ``process_class``    |
    |                       | option in the ``Simulation`` section) and used |
    |                       | to distribute the initial node states over the |
    |                       | network. While it is possible for generic      |
    |                       | classes to override, the format of this        |
    |                       | section should be so that the option names     |
    |                       | should be the names of the network node states |
    |                       | used by the process and their values should be |
    |                       | the fraction of nodes, alternatively the       |
    |                       | number of nodes, that will be  assigned to     |
    |                       | each state initially. If the sum of the states |
    |                       | add up to the size of the network the exact    |
    |                       | number of nodes will be used. If not, a        |
    |                       | fraction of the network equal to (network size |
    |                       | * state dist)/(sum of all state dist) will be  |
    |                       | used. I.e. normalized. It is recommended to    |
    |                       | either use exact numbers or fractions of the   |
    |                       | network size here for readability. The state   |
    |                       | names must match those specified by the        |
    |                       | network process class. If this section is left |
    |                       | out an equal number of nodes are allocated to  |
    |                       | each state.                                    |
    +-----------------------+------------------------------------------------+
    | EdgeStateDistribution | This is a special section, and analogous to    |
    |                       | the NodeStateDistribution described above but  |
    |                       | for edges.                                     |
    +-----------------------+------------------------------------------------+
    | Output                | This section contains options controlling      |
    |                       | simulation output and saving of data.          |
    |                       | See table of Output section options below for  |
    |                       | specific settings.                             |
    +-----------------------+------------------------------------------------+
    | Logging               | Contains options on software log output for    |
    |                       | nepidemix.                                     |
    +-----------------------+------------------------------------------------+
    


    Configuration options

    Below are tables listing available options for sections having them.


    +-----------------------+------------------------------------------------+
    |                       Simulation section options                       |
    +-----------------------+------------------------------------------------+
    |      Option key       |         Explanation                            |
    +=======================+================================================+
    | iterations            | Run the simulation this many iterations.       |
    +-----------------------+------------------------------------------------+
    | dt                    | The time step taken each iteration. Should be  |
    |                       | a fraction in the range 0,1.                   |
    +-----------------------+------------------------------------------------+
    | process_class         | This is the name of the process object.        |
    |                       | See ``nepidemix.process`` or tutorial for      |
    |                       | options.                                       |
    +-----------------------+------------------------------------------------+
    | process_class_module  | This is the python module/package where the    |
    |                       | class given in the option process_class        |
    |                       | resides. Default: ``nepidemix.process`` for    |
    |                       | built-in processes. Use the base name of your  |
    |                       | own file if you programmed your own process in |
    |                       | python. See tutorial for examples.             |
    |                       | Optional.                                      |
    +-----------------------+------------------------------------------------+
    | network_func          | This is the name of the network generation     |
    |                       | function. See                                  |
    |                       |``nepidemix.utilities.networkgeneratorwrappers``|
    |                       | for a list of network generation functions.    |
    +-----------------------+------------------------------------------------+
    | network_func_module   | This is the python module where the network    |
    |                       | function resides. If you do not write your own |
    |                       | network generation functions this can be left  |
    |                       | undefined. Optional.                           |
    +-----------------------+------------------------------------------------+
    | network_init          | This switch (on/off, true/false, yes/no, 1/0)  |
    |                       | is optional (default value true) and tells the |
    |                       | simulation if the network should be            |
    |                       | initialized by the current process or not.     |
    |                       | Note that not initializing the network may     |
    |                       | lead to errors or strange behavior. Only       |
    |                       | switch off if network is loaded from disk and  |
    |                       | you don't want it to be re-initialized with    |
    |                       | new state (thus keeping the states), or if the |
    |                       | network is initialized by some other           |
    |                       | mechanism.                                     |
    +-----------------------+------------------------------------------------+
    | module_paths          | This is an optional list (comma-separated) of  |
    |                       | directory paths that the simulation will add   |
    |                       | to the python path before loading the network  |
    |                       | generation and process routines. Useful if you |
    |                       | have written your own functions that reside in |
    |                       | some directory not on the path. See the        |
    |                       | tutorial for examples on how this option is    |
    |                       | used.                                          |
    +-----------------------+------------------------------------------------+
    
    +----------------------------+-------------------------------------------+
    |                         Output section options                         |
    +----------------------------+-------------------------------------------+
    |        Option key          |                Explanation                |
    +============================+===========================================+
    | output_dir                 | Output directory where files will be      |
    |                            | saved.                                    | 
    |                            | The directory must exist and be writable. |
    +----------------------------+-------------------------------------------+
    | base_name                  | This is the base name of all files        | 
    |                            | generated by the run.                     |
    +----------------------------+-------------------------------------------+
    | unique                     | Optional (default value true) switch      |
    |                            | (on/off, true/false, yes/no, 1/0). If     |
    |                            | unique is defined as true, yes, 1, or on, |
    |                            | unique file names will be created (time   |
    |                            | stamp added).                             |
    +----------------------------+-------------------------------------------+
    | save_config                | Switch (on/off, true/false, yes/no, 1/0). |
    |                            | If this is true, yes, 1, or on, a copy of |
    |                            | the full program config, plus an Info     |
    |                            | section will be saved.                    |
    +----------------------------+-------------------------------------------+
    | save_node_state            | Optional (default value true) switch      |
    |                            | (on/off, true/false, yes/no, 1/0).        |            
    |                            | If this is true/yes/on, the network nod   |
    |                            | states will be sampled and saved as a csv |
    |                            | file.                                     |
    |                            | Note: only valid if the current process   |
    |                            | support node updates. If not, nothing     |
    |                            | will be saved.                            |
    +----------------------------+-------------------------------------------+
    | save_node_state_interval   | Optional (default value 1). Sample nodes  |
    |                            | every <value> iterations. Value should be |
    |                            | an integer >= 1. Note, initial and final  |
    |                            | node state counts are always saved even   |
    |                            | if they are not covered by the interval.  |
    +----------------------------+-------------------------------------------+
    | save_network_compress_file | Optional (default value true) switch      |
    |                            | (on/off, true/false, yes/no, 1/0).        |
    |                            | Denotes if the saved network files should |
    |                            | be bz2 compressed.                        |
    +----------------------------+-------------------------------------------+


    +----------------------------+-------------------------------------------+
    |                        Logging section options                         |
    +----------------------------+-------------------------------------------+
    |        Option key          |                Explanation                |
    +============================+===========================================+
    | level                      | Optional (default value DEBUG).           |
    |                            | Must be one of DEBUG/INFO/WARN/SILENT.    |
    +----------------------------+-------------------------------------------+

    """
    # Configuration file constants.
    CFG_SECTION_OUTPT =  "Output"
    CFG_SECTION_SIM = "Simulation"
    CFG_SECTION_LOG = "Logging"
    CFG_SECTION_MOD = "ProcessParameters"

    # This section is used store information about the sim.
    CFG_SECTION_INFO = "Info" 
    # This section carry the network parameters
    CFG_SECTION_NETWORK = "NetworkParameters"
    # This section is used to distribute states among the nodes.
    CFG_SECTION_NODE_STATE_DIST = "NodeStateDistribution"
    # This section is used to distribute states among the nodes.
    CFG_SECTION_EDGE_STATE_DIST = "EdgeStateDistribution"

    # Parameter names.
    CFG_PARAM_mod_path = "module_paths"
    CFG_PARAM_outputDir = "output_dir"
    CFG_PARAM_baseFileName = "base_name"
    CFG_PARAM_uniqueFileName = "unique"
    CFG_PARAM_dt = "dt"
    CFG_PARAM_iterations = "iterations"
    CFG_PARAM_process_name = "process_class"
    CFG_PARAM_process_module = "process_class_module"
    CFG_PARAM_network_name = "network_func"
    CFG_PARAM_network_module = "network_func_module"
    CFG_PARAM_save_config = "save_config"
    CFG_PARAM_network_init = "network_init"

    # Info parameters.
    CFG_PARAM_execute_time = "sim_exec_time"
    CFG_PARAM_avgclust = "avg_clustering"
    CFG_PARAM_avgdegree = "avg_degree"

    # Network output parameters
    CFG_PARAM_save_network = "save_network"
    CFG_PARAM_save_network_interval = "save_network_interval"
    CFG_PARAM_save_network_format = "save_network_format"
    CFG_PARAM_save_network_compress_file = "save_network_compress_file"
    # Node output parameters
    CFG_PARAM_save_node_state = "save_node_state"
    CFG_PARAM_save_node_state_interval = "save_node_state_interval"
    # Edge output parameters
    CFG_PARAM_save_edge_state = "save_edge_state"
    CFG_PARAM_save_edge_state_interval = "save_edge_state_interval"

    def __init__(self):
        """
        Initialization method.
        
        """
        self.process = None
        self.network = None
        self.stateSamples = None
        self.save_config = False
        self.settings = None
        self.TIME_FIELD_NAME = "Time"


    def execute(self):
        """ 
        Execute simulation. 
        
        The simulation must be configured before this method is called.
        
        """
        nwcopytime = 0
        startTime = time.time()
        logger.info("Running simulation.")
        logger.info("Simulation will cover {0} months."\
                        .format(self.iterations*self.dt))

        # If the network is to be saved, then save the initial config.
        if self.saveNetwork == True:
            self._saveNetwork(number = 0)
        
        # Create state count arrays, count and add the initial states.

        # Add the vector as a np array to allow for easy numerical processing later.
        self.stateSamples = []

        # Add entry for time 0.
        self.stateSamples.append(dict([ (s,str(v)) for s,v in self.network.graph.iteritems()]))
        logger.info("Initial node state sample vector: {0}".format(self.stateSamples))


        readNetwork = self.network
        logger.info("Process will leave topology constant?: {0}".format(self.process.constantTopology))
        if self.process.constantTopology == True:
            writeNetwork = readNetwork.copy()
        else:
            writeNetwork = networkx.Graph()
            writeNetwork.graph = readNetwork.graph.copy()

        for it in range(self.iterations):
            # Update nodes.
            if self.process.constantTopology == False or self.process.runNodeUpdate == True:
                # Go over all nodes.

                for n in readNetwork.nodes_iter(data = True):
                    oldstate = self.process.deduceNodeState(n)
                    nc = (n[0], n[1].copy())
                    nc = self.process.nodeUpdateRule(nc, 
                                                     readNetwork, 
                                                     self.dt)
                    writeNetwork.add_node(nc[0], nc[1])
                    newstate = self.process.deduceNodeState(nc)

                    if newstate != oldstate:
                        writeNetwork.graph[newstate] = \
                            readNetwork.graph.get(newstate, 0) + 1

                        if readNetwork.graph.has_key(oldstate):
                            writeNetwork.graph[oldstate] =\
                                readNetwork.graph[oldstate] - 1


                
            # Update edges.
            if self.process.constantTopology == False or self.process.runEdgeUpdate == True:
                for e in readNetwork.edges_iter(data = True):
                    oldstate = self.process.deduceEdgeState(e)
                    ne = (e[0], e[1], e[2].copy())
                    ne = self.process.edgeUpdateRule(ne,
                                                     readNetwork,
                                                     self.dt)
                    writeNetwork.add_edge(ne[0], ne[1], ne[2])
                    newstate = self.process.deduceEdgeState(ne)

                    if newstate != oldstate:

                        writeNetwork.graph[newstate] = \
                            readNetwork.graph.get(newstate, 0) + 1

                        if readNetwork.graph.has_key(oldstate):
                            writeNetwork.graph[oldstate] =\
                                readNetwork.graph[oldstate] - 1

        
      
            if self.process.constantTopology == False or self.process.runNetworkUpdate == True:
                 writeNetwork = self.process.networkUpdateRule(writeNetwork, self.dt)

            writeNetwork.graph[self.TIME_FIELD_NAME] = readNetwork.graph[self.TIME_FIELD_NAME] + self.dt
            self.network = writeNetwork
            writeNetwork = readNetwork
            readNetwork = self.network
            
            if self.process.constantTopology == False:
                writeNetwork.clear()
            # Always update the graph

            writeNetwork.graph = readNetwork.graph.copy()

            # Check if we should save node state this iteration.
            # it +1 is checked as the 0th is always saved before the loop.
            # Also always save the last result.
            if  self.saveNodeState and \
                    ((self.saveNodeStateInterval >0 and (it+1)%(self.saveNodeStateInterval) == 0)\
                         or (it == self.iterations -1 )):
                #self.stateSamples.append(collections.OrderedDict({self.TIME_FIELD_NAME:0.0}))
                # Add the mean field states.
                #self.stateSamples[-1].update(self.network.graph)
#                self.stateSamples.append(self.network.graph.copy())
                self.stateSamples.append(dict([ (s,str(v)) for s,v in self.network.graph.iteritems()]))
            # Check network saving. Same here as for states above:
            # look at iteration +1, as it is done after execution of the rules.
            if self.saveNetwork == True and ( \
                ( self.saveNetworkInterval >0 \
                      and (it+1)%(self.saveNetworkInterval) == 0 )\
                    or it == (self.iterations-1) ):
                self._saveNetwork(number= (it+1))
        
        logger.info("Simulation done.")
        endTime = time.time()
        logger.info("Total execution time: {0} s.".format(endTime-startTime))
        if self.settings != None:
            self.settings.set(self.CFG_SECTION_INFO, 
                              self.CFG_PARAM_execute_time,(endTime-startTime))


    def configure(self, settings):
        """
        Configure simulation.
        
        Parameters
        ----------
        
        settings : NepidemiXConfigParser, ConfigParser compatible
           The settings in a ConfigParser compatible datastructure.
           
        See Also
        --------
        
        nepidemix.NepidemiXConfigParser

        """

        self.settings = settings
        if not self.settings.has_section(self.CFG_SECTION_INFO):
            self.settings.add_section(self.CFG_SECTION_INFO)

        try:
            try:
                self.outputDir = settings.get(self.CFG_SECTION_OUTPT, 
                                          self.CFG_PARAM_outputDir)
                logger.info("Output directory set to '{0}'".format(self.outputDir))
                self.baseFileName = settings.get(self.CFG_SECTION_OUTPT, 
                                             self.CFG_PARAM_baseFileName)
                self.save_config = settings.getboolean(self.CFG_SECTION_OUTPT,
                                                       self.CFG_PARAM_save_config)

                self.iterations = settings.getint(self.CFG_SECTION_SIM, 
                                                  self.CFG_PARAM_iterations)
                logger.info("# iterations = {0}".format(self.iterations))
                self.dt = settings.getfloat(self.CFG_SECTION_SIM, 
                                            self.CFG_PARAM_dt);
                logger.info("dt = {0}".format(self.dt))

            except NepidemiXBaseException as err:
                logger.error("Missing mandatory config option : {0}".format(err))
                sys.exit()

            for pth in settings.getrange(self.CFG_SECTION_SIM,
                                    self.CFG_PARAM_mod_path,
                                    default=[]):
                abspth = os.path.abspath(pth)
                logger.info("Adding '{0}' to python path.".format(abspth))
                sys.path.append(abspth)
                
            self.saveNodeStateInterval = settings.getint(self.CFG_SECTION_OUTPT,
                                                         self.CFG_PARAM_save_node_state_interval, 
                                                         default=1)



            self.saveNodeState = settings.getboolean(self.CFG_SECTION_OUTPT,
                                                         self.CFG_PARAM_save_node_state,
                                                     default=True)
    

            self.saveEdgeStateInterval = settings.getint(self.CFG_SECTION_OUTPT,
                                                         self.CFG_PARAM_save_edge_state_interval,
                                                         default=1)

            self.saveEdgeState = settings.getboolean(self.CFG_SECTION_OUTPT,
                                                     self.CFG_PARAM_save_edge_state,
                                                     default = True)
            
            # If there is no option to set a unique file name take it as true.
            # If there is one we have to check if it is set to true.
            # Then update name.
            if (not settings.has_option(self.CFG_SECTION_OUTPT, 
                                   self.CFG_PARAM_uniqueFileName)
                ) or (settings.getboolean(self.CFG_SECTION_OUTPT, 
                                          self.CFG_PARAM_uniqueFileName)
                      ) ==  True:
                self.baseFileName = self.baseFileName + '_'+\
                    "-".join(("_".join(time.ctime().split())).split(':'))
            logger.info("Base file name set to: '{0}'".format(self.baseFileName))

                
        except NepidemiXBaseException as err:
            logger.error("Missing mandatory config section : {0}".format(err))
            sys.exit()
            


        # Construct process.
        # Make dictionary from the settings.
        dparams = settings.evaluateSection(self.CFG_SECTION_MOD)
        process_name = settings.get(self.CFG_SECTION_SIM, 
                                  self.CFG_PARAM_process_name)
        process_module = settings.get(self.CFG_SECTION_SIM, 
                                      self.CFG_PARAM_process_module,
                                      default = 'nepidemix.process')
        self.process = _import_and_execute(process_name, process_module,dparams)
        logger.info("Created '{0}' object"
                    .format(process_name))
    
        # Construct and initialize network.
        dparams = settings.evaluateSection(self.CFG_SECTION_NETWORK)
        nwork_name = settings.get(self.CFG_SECTION_SIM, 
                                  self.CFG_PARAM_network_name)
        nwork_module = settings.get(self.CFG_SECTION_SIM, 
                                    self.CFG_PARAM_network_module,
                                    default = 'nepidemix.utilities.networkgeneratorwrappers')
        self.network = _import_and_execute(nwork_name, nwork_module,dparams)
        # Change the standard dictionary in the NetworkX graph to an ordered one.
        self.network.graph = collections.OrderedDict(self.network.graph)
        # Add an attribute for time.
        self.network.graph[self.TIME_FIELD_NAME] = 0.0
        logger.info("Created '{0}' network with {1} nodes." \
                       .format(nwork_name, len(self.network)))
        # Save the average clustering to info section
        self.settings.set(self.CFG_SECTION_INFO, 
                          self.CFG_PARAM_avgclust,
                          networkx.average_clustering(self.network))
        # And the average degree
        self.settings.set(self.CFG_SECTION_INFO,
                          self.CFG_PARAM_avgdegree,
                          sum(networkx.degree(self.network).values())\
                              /float(len(self.network)))
        # Initialize the states
        # Check if init should be performed.
        if (not settings.has_option(self.CFG_SECTION_SIM, self.CFG_PARAM_network_init))\
                or settings.getboolean(self.CFG_SECTION_SIM, self.CFG_PARAM_network_init):
            # Nodes
            if settings.has_section(self.CFG_SECTION_NODE_STATE_DIST):
#                attDict = dict(settings.items(self.CFG_SECTION_NODE_STATE_DIST))
                attDict = settings.evaluateSection(self.CFG_SECTION_NODE_STATE_DIST)
            else:
                attDict = {}
            self.process.initializeNetworkNodes(self.network, **attDict)
            
            # Edges
            if settings.has_section(self.CFG_SECTION_EDGE_STATE_DIST):
                attDict = settings.evaluateSection(self.CFG_SECTION_EDGE_STATE_DIST)
            else:
                attDict = {}
            self.process.initializeNetworkEdges(self.network, **attDict)
            
            # The network itself.
            # Right now it doesn't have a configuration section.
            self.process.initializeNetwork(self.network)

        # Network save options
        self.saveNetwork = settings.getboolean(self.CFG_SECTION_OUTPT,
                                               self.CFG_PARAM_save_network,
                                               default=False)

        self.saveNetworkInterval = settings.getint(self.CFG_SECTION_OUTPT,
                                                   self.CFG_PARAM_save_network_interval,
                                                   default = 0)

        self.saveNetworkFormat = settings.get(self.CFG_SECTION_OUTPT,
                                              self.CFG_PARAM_save_network_format,
                                              default = 'gpickle')

        self.saveNetworkFormatCompress = \
            settings.getboolean(self.CFG_SECTION_OUTPT,
                                self.CFG_PARAM_save_network_compress_file,
                                default = True)

            
      

    def saveData(self):
        """ 
        Save any computed data as per configuration.
        
        If execute() has not yet been run (i.e. no data exist) an error message
        is printed.

        """
        logger.info("Saving data.")
        if self.saveNodeState == True:
            if self.stateSamples == None:
                logger.error("No data to save exists. Run execute() first.")
            elif self.process.runNodeUpdate == True:
                stateDataFName = self.outputDir+"/"+self.baseFileName+"_state_count.csv"
                try:
                    with open(stateDataFName, 'wb') as stateDataFP:
                        stateDataWriter = csv.writer(stateDataFP)
                        # Write labels in first row
                        keys = self.network.graph.keys()
                        stateDataWriter.writerow(keys)
                        for row in self.stateSamples:
                            stateDataWriter.writerow([row.get(k,0) for k in keys])
                except IOError:
                    logger.error("Could not open file '{0}' for writing!"\
                                     .format(stateDataFName))

        if self.save_config == True:
            if self.settings == None:
                logger.error("No settings to save exists.")
            else:
                configDataFName = self.outputDir+"/"+self.baseFileName+".ini"
                try:
                    with open(configDataFName, 'wb') as configDataFP:
                        self.settings.write(configDataFP)
                except IOError:
                    logger.error("Could not open file '{0}' for writing!"\
                                             .format(configDataFName))
        logger.info("Saving done")

    def _saveNetwork(self, number = -1):
        """
        Save network to file.
        
        Currently gpickle (uncompressed or bz2 compressed) is supported.
        
        Parameters
        ----------
        
        number : int, optional 
           If >0 this number will be appended (zero padded) to the file name.
           Default value -1.

        """

        sveBaseName = "{0}/{1}".format(self.outputDir,
                                           self.baseFileName)
        if number >= 0:
            sveBaseName = sveBaseName +"_{0:010}".format(number)

        sveBaseName = sveBaseName + ".{0}".format(self.saveNetworkFormat)

        if self.saveNetworkFormatCompress == True:
            sveBaseName = sveBaseName + '.bz2'

        if self.saveNetworkFormat == 'gpickle':
            networkx.readwrite.gpickle.write_gpickle(self.network, 
                                                     sveBaseName)
        elif self.saveNetworkFormat == 'GraphML':  
            networkx.readwrite.graphml.write_graphml(self.network, 
                                                     sveBaseName)
        else:
            logger.error("Unknown file format {0}".format(\
                    self.saveNetworkFormat))

#        logger.info("Wrote initial graph to '{0}'.".format(sveBaseName))

                                                       
def _import_and_execute(name, modules, parameters):
    """
    Utility function that loads a function or class object from a module 
    and executes it.

    Basically perform a 'from <modules> import <name>'
    Then executes name with the parameters.
    Finally the name is unloaded from the name space.

    Parameters
    ----------

    name : str
       String containing the name of the function/class to load.

    modules : str
       String containing the standard dot separated modules path

    parameters : dict
       Dictionary of function parameters. Will be sent in with a **kwargs style
       call. Thus if your function has a fixed parameter list make sure that the
       dictionary keys match the names.

    Returns 
    -------
    
    retval : special
       The result of the function call.
    
    """

    retval = None
    # First have a go att importing from absolute.
    try:
        exec("from {0} import {1} as nm_impexf".format(modules, name))
        # Execute.
    except ImportError as e:
        # If that fails try to import 'dotted'
        try:
            exec("import {0}.{1} as nm_impexf".format(modules, name))
        except ImportError as e:
            emsg = "Could not import {0} from {1}, nor {0}.{1}; Check that the module and class names are correct."\
                .format(name, modules)
            logger.error(emsg)
            raise NepidemiXBaseException(emsg)

    if parameters==None:
        retval = nm_impexf()
    else:
        retval = nm_impexf(**parameters)
    # Remove from name space.
    del nm_impexf
    # Return
    return retval
