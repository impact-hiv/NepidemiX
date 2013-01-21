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
from collections import OrderedDict


# Local imports

from nepidemix import process


from nepidemix.exceptions import NepidemiXBaseException

from nepidemix.utilities import NepidemiXConfigParser

from nepidemix.version import full_version

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
    | node_init             | This switch (on/off, true/false, yes/no, 1/0)  |
    |                       | is optional (default value true) and tells the |
    |                       | simulation if the network nodes should be      |
    |                       | initialized by the current process or not.     |
    |                       | Note: This option is only interpreted if       |
    |                       | network_init is set to on (true, yes, 1) and   |
    |                       | is ignored otherwise. Optional. Default: true  |
    +-----------------------+------------------------------------------------+
    | edge_init             | This switch (on/off, true/false, yes/no, 1/0)  |
    |                       | is optional (default value true) and tells the |
    |                       | simulation if the network edges should be      |
    |                       | initialized by the current process or not.     |
    |                       | Note: This option is only interpreted if       |
    |                       | network_init is set to on (true, yes, 1) and   |
    |                       | is ignored otherwise. Optional. Default: true. |
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
    | include_files         | Optional list (comma-separated) containing     |
    |                       | names of additional configuration files to     |
    |                       | include. The files will be read in order and   |
    |                       | their sections added to the configuration.     |
    |                       | This allows for splitting of large             |
    |                       | configuration files into logical sections      |
    |                       | and store them in individual files.            |
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
    | save_state_count           | Optional (default value true) switch      |
    |                            | (on/off, true/false, yes/no, 1/0).        |            
    |                            | If this is true/yes/on, the network node  |
    |                            | states will be counted and saved as a csv |
    |                            | file.                                     |
    |                            | Note: only valid if the current process   |
    |                            | support node updates. If not, nothing     |
    |                            | will be saved.                            |
    +----------------------------+-------------------------------------------+
    | save_state_count_interval  | Optional (default value 1). Count nodes   |
    |                            | every <value> iterations. Value should be |
    |                            | an integer >= 1. Note, initial and final  |
    |                            | node state counts are always saved even   |
    |                            | if they are not covered by the interval.  |
    +----------------------------+-------------------------------------------+
    | save_state_influx          | Optional (default value true) switch      |
    |                            | (on/off, true/false, yes/no, 1/0).        |            
    |                            | If this is true/yes/on, the network node  |
    |                            | states influx (total num new nodes in     |
    |                            | state) will be saved to a csv file.       |
    |                            | Note: only valid if the current process   |
    |                            | support node updates. If not, nothing     |
    |                            | will be saved.                            |
    +----------------------------+-------------------------------------------+
    | save_state_influx_interval | Optional (default value 1). Save influx   |
    |                            | every <value> iteration. Value            |
    |                            | is integer >= 1. Note, initial and final  |
    |                            | node state influx are always saved even   |
    |                            | if they are not covered by the interval.  |
    +----------------------------+-------------------------------------------+
    | save_network_compress_file | Optional (default value true) switch      |
    |                            | (on/off, true/false, yes/no, 1/0).        |
    |                            | Denotes if the saved network files should |
    |                            | be bz2 compressed.                        |
    +----------------------------+-------------------------------------------+
    | save_state_transition_cnt  | Optional (default value false) switch     |
    |                            | (on/off true/false, yes/no, 1/0).         |
    |                            | If set to true a csv file with saving the |
    |                            | count of every possibly triggered         |
    |                            | transition in every time step.            |
    |                            | The file format is time in first column,  |
    |                            | old state in second column, and number    |
    |                            | of transitions to destination state in    |
    |                            | the following columns. Destination states |
    |                            | are given by the first row.               |
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
    
    # Simulation parameters
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
    CFG_PARAM_node_init = "node_init"
    CFG_PARAM_edge_init = "edge_init"
    CFG_PARAM_include_files = "include_files"

    # Info parameters.
    CFG_PARAM_execute_time = "sim_exec_time"
    CFG_PARAM_avgclust = "avg_clustering"
    CFG_PARAM_avgdegree = "avg_degree"
    CFG_PARAM_nepidemix_version = "NepidemiX_version";

    # Network output parameters
    CFG_PARAM_save_network = "save_network"
    CFG_PARAM_save_network_interval = "save_network_interval"
    CFG_PARAM_save_network_format = "save_network_format"
    CFG_PARAM_save_network_compress_file = "save_network_compress_file"
    CFG_PARAM_save_state_count = "save_state_count"
    CFG_PARAM_save_state_count_interval = "save_state_count_interval"
    CFG_PARAM_save_state_influx = "save_state_influx"
    CFG_PARAM_save_state_influx_interval = "save_state_influx_interval"
    CFG_PARAM_save_node_rule_transition_count = "save_state_transition_cnt"

    # Names of fields in the network graph dictionary.
    TIME_FIELD_NAME = "Time"
    STATE_COUNT_FIELD_NAME = "state_count"
    STATE_INFLUX_FIELD_NAME = "state_influx"

    

    def __init__(self):
        """
        Initialization method.
        
        """
        self.process = None
        self.network = None
        self.stateSamples = None
        self.stateInFlux = None

        self.save_config = False
        self.settings = None


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

        self.stateSamples = {}
        
        self.stateSamples[self.STATE_COUNT_FIELD_NAME] = []
        self.stateSamples[self.STATE_INFLUX_FIELD_NAME] = []
    
        # Add entry for time 0.
        for k in self.stateSamples:
            # Create dictionary.
            countDict = {}
            # Insert time stamp.
            countDict[self.TIME_FIELD_NAME] = 0.0
            # Copy data.

            countDict.update(dict([ (s,str(v)) for s,v in self.network.\
                                        graph[k].iteritems()]))

            self.stateSamples[k].append(countDict)

        # Transition counts should be saved.
        self.nodeRuleTransCnt = [(0.0,{})]

        logger.info("Initial node state count vector: {0}".format(self.stateSamples[self.STATE_COUNT_FIELD_NAME]))
        logger.info("Initial node state influx vector: {0}".format(self.stateSamples[self.STATE_INFLUX_FIELD_NAME]))

        readNetwork = self.network
        logger.info("Process will leave topology constant?: {0}".format(self.process.constantTopology))
        if self.process.constantTopology == True:
            writeNetwork = readNetwork.copy()
        else:
            writeNetwork = networkx.Graph()
            for stk in self.stateSamples:
                writeNetwork.graph[stk] = readNetwork.graph[stk].copy()

        for it in range(self.iterations):
            # Add a node transition count array for this iteration (update timestamp and copy data array).
            self.nodeRuleTransCnt.append((self.nodeRuleTransCnt[-1][0] + self.dt, {}))
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

                        # Debug code belonging to 
                        # own = int(writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][oldstate])
                        # nwn = int(writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][newstate])
                        # orn = int(readNetwork.graph[self.STATE_COUNT_FIELD_NAME][oldstate])
                        # nrn = int(readNetwork.graph[self.STATE_COUNT_FIELD_NAME][newstate])
                        
                        # Update count
                        writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][newstate] += 1
                        writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][oldstate] -= 1
                        
#                         if writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][newstate] == nwn or \
#                                 writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][oldstate] == own or \
#                                 readNetwork.graph[self.STATE_COUNT_FIELD_NAME][newstate] != nrn or \
#                                 readNetwork.graph[self.STATE_COUNT_FIELD_NAME][oldstate] != orn:
#                             logger.error("""Error in state counts! 
# newstate: write original = {0}, write update = {1}
# newstate: read original = {2}, read update = {3}
# oldstate: write original = {4}, write update = {5}
# oldstate: read original = {6}, read update = {7}

# """.format(nwn,
#            writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][newstate],
#            nrn,
#            readNetwork.graph[self.STATE_COUNT_FIELD_NAME][newstate],
#            own,
#            writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][oldstate],
#            orn,
#            readNetwork.graph[self.STATE_COUNT_FIELD_NAME][oldstate]))
#                             exit(-1)


                        # Update influx
                        writeNetwork.graph[self.STATE_INFLUX_FIELD_NAME][newstate] += 1
                        # Update node rule trigger count.
                        self.nodeRuleTransCnt[-1][1].setdefault(oldstate, {})
                        self.nodeRuleTransCnt[-1][1][oldstate].setdefault(newstate, 0)
                        self.nodeRuleTransCnt[-1][1][oldstate][newstate] += 1

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
                        # Update count
                        writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][newstate] += 1
                        writeNetwork.graph[self.STATE_COUNT_FIELD_NAME][oldstate] -= 1
                        # Update influx
                        writeNetwork.graph[self.STATE_INFLUX_FIELD_NAME][newstate] += 1
        
      
            if self.process.constantTopology == False or self.process.runNetworkUpdate == True:
                 writeNetwork = self.process.networkUpdateRule(writeNetwork, self.dt)

            writeNetwork.graph[self.TIME_FIELD_NAME] = readNetwork.graph[self.TIME_FIELD_NAME] + self.dt
            self.network = writeNetwork
            writeNetwork = readNetwork
            readNetwork = self.network
            
            if self.process.constantTopology == False:
                writeNetwork.clear()
            # Always update the graph for each sub dictionary.
            for k in self.stateSamples:
                writeNetwork.graph[k] = copy.deepcopy(readNetwork.graph[k])
                # Check if we should save node state this iteration.
                # it +1 is checked as the 0th is always saved before the loop.
                # Also always save the last result.
                if  self.saveStates[k] and \
                        ((self.saveStatesInterval[k] >0 and (it+1)%(self.saveStatesInterval[k]) == 0)\
                             or (it == self.iterations -1 )):
                    # Add the mean field states.
                    countDict = {}
                    # Create dictionary.
                    # Insert time stamp.
                    countDict[self.TIME_FIELD_NAME] = self.network.graph[self.TIME_FIELD_NAME]
                    # Copy data.
                    countDict.update(dict([ (s,str(v)) for s,v in self.network.graph[k].iteritems()]))
                    # Add to current list of samples.
                    self.stateSamples[k].append(countDict)
                                
                            
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

        
        self.includeFiles = settings.getrange(self.CFG_SECTION_SIM,
                                              self.CFG_PARAM_include_files,
                                              default = [],
                                              add_if_not_existing = False)
            
        if len(self.includeFiles) > 0:
            logger.info("Files {0} will be included.".format(", ".join(self.includeFiles)))
            for fileName in self.includeFiles:
                with open(fileName) as fp:
                    settings.readfp(fp)


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

        # Set/update verision info field.
        self.settings.set(self.CFG_SECTION_INFO, 
                          self.CFG_PARAM_nepidemix_version,
                          full_version)

        # Construct and initialize network.
        dparams = settings.evaluateSection(self.CFG_SECTION_NETWORK)
        nwork_name = settings.get(self.CFG_SECTION_SIM, 
                                  self.CFG_PARAM_network_name)
        nwork_module = settings.get(self.CFG_SECTION_SIM, 
                                    self.CFG_PARAM_network_module,
                                    default = 'nepidemix.utilities.networkgeneratorwrappers')
        self.network = _import_and_execute(nwork_name, nwork_module,dparams)
        # Change the standard dictionary in the NetworkX graph to an ordered one.
        self.network.graph = OrderedDict(self.network.graph)

        if self.network.graph.has_key(self.STATE_COUNT_FIELD_NAME) == False:
            # Create a dictionary for the state counts.
            self.network.graph[self.STATE_COUNT_FIELD_NAME] = OrderedDict()
        if self.network.graph.has_key(self.STATE_INFLUX_FIELD_NAME) == False:
            # Create a dictionary for the state influx.
            self.network.graph[self.STATE_INFLUX_FIELD_NAME] = OrderedDict()

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

            # Add an attribute for time/set time to zero.
            self.network.graph[self.TIME_FIELD_NAME] = 0.0

            # Nodes
            if settings.getboolean(self.CFG_SECTION_SIM, 
                                   self.CFG_PARAM_node_init, default = True):
                if settings.has_section(self.CFG_SECTION_NODE_STATE_DIST):
                    attDict = settings.evaluateSection(self.CFG_SECTION_NODE_STATE_DIST)
                else:
                    attDict = {}
                self.process.initializeNetworkNodes(self.network, **attDict)
            else:
                logger.info("Skipping node initialization.")
            # Edges
            if settings.getboolean(self.CFG_SECTION_SIM, 
                                   self.CFG_PARAM_edge_init, default = True):
                if settings.has_section(self.CFG_SECTION_EDGE_STATE_DIST):
                    attDict = settings.evaluateSection(self.CFG_SECTION_EDGE_STATE_DIST)
                else:
                    attDict = {}
                self.process.initializeNetworkEdges(self.network, **attDict)
            else:
                logger.info("Skipping edge initialization.") 
            # The network itself.
            # Right now it doesn't have a configuration section.
            self.process.initializeNetwork(self.network)


        self.saveStatesInterval = {}

        self.saveStatesInterval[self.STATE_COUNT_FIELD_NAME] = \
            settings.getint(self.CFG_SECTION_OUTPT,
                            self.CFG_PARAM_save_state_count_interval, 
                            default=1)

        self.saveStatesInterval[self.STATE_INFLUX_FIELD_NAME] = \
            settings.getint(self.CFG_SECTION_OUTPT,
                            self.CFG_PARAM_save_state_influx_interval, 
                            default=1)


        self.saveStates = {}

        self.saveStates[self.STATE_COUNT_FIELD_NAME] = \
            settings.getboolean(self.CFG_SECTION_OUTPT,
                                self.CFG_PARAM_save_state_count,
                                default=True)

        self.saveStates[self.STATE_INFLUX_FIELD_NAME] = \
            settings.getboolean(self.CFG_SECTION_OUTPT,
                                self.CFG_PARAM_save_state_influx,
                                default=True)


        self.saveNodeRuleTransitionCount = \
            settings.getboolean(self.CFG_SECTION_OUTPT,
                                self.CFG_PARAM_save_node_rule_transition_count,
                                default = False)

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
        if True in self.saveStates.values():
            if self.stateSamples == None:
                logger.error("No data to save exists. Run execute() first.")
            else:
                for sampleName in self.stateSamples:
                    if self.saveStates[sampleName] == True:
                        stateDataFName = self.outputDir+"/"+self.baseFileName+"_{0}.csv".format(sampleName)
                        logger.info("File = '{0}'".format(stateDataFName))
                        try:
                            with open(stateDataFName, 'wb') as stateDataFP:
                                stateDataWriter = csv.writer(stateDataFP)
                                              
                                # Keys are time stamp
                                keys = [self.TIME_FIELD_NAME]
                                # and labels
                                keys.extend(self.network.graph[sampleName].keys())

                                # Write labels in first row
                                stateDataWriter.writerow(keys)
                                # Write data.
                                for row in self.stateSamples[sampleName]:
                                    stateDataWriter.writerow([row.get(k,0) for k in keys])
                        except IOError:
                            logger.error("Could not open file '{0}' for writing!"\
                                             .format(stateDataFName))

        if self.saveNodeRuleTransitionCount == True:
            nodeRTFName = os.path.join(self.outputDir,self.baseFileName+"_nodeTrans.csv")
            logger.info("Saving Node Transition Counts to file {0}".format(nodeRTFName))
            try:
                with open(nodeRTFName, 'wb') as nodeRTFP:
                    nodeRTDataWriter = csv.writer(nodeRTFP)
                    # Compute state matrix dimensions and keys.
                    globOldStates = set()
                    globNewStates = set()
                    for ts, nRTData in self.nodeRuleTransCnt:
                        globOldStates.update(nRTData.keys())
                        for oldState, tCounts in nRTData.iteritems():
                            globNewStates.update(tCounts.keys())
                    csvrw = [self.TIME_FIELD_NAME, "New (col) / Old (row)"]
                    csvrw.extend(globNewStates)
#                    logger.debug(csvrw)
                    nodeRTDataWriter.writerow(csvrw)
                    # Go through the data again in the order given by the sets and save a full matrix.
                    for ts, nRTData in self.nodeRuleTransCnt:
                        # Update state matrix
                        for oldState in globOldStates:
                            rw = [ts,oldState]
                            rw.extend([ nRTData.get(oldState,{}).get(newState,0) for newState in globNewStates ])
                            nodeRTDataWriter.writerow(rw)
            except IOError:
                logger.error("Could not open or write to file '{0}'!".format(nodeRTFName))
                
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
