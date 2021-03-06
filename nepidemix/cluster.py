"""
=======
Cluster 
=======

Code supporting parallel cluster execution of simulations.

This module was mainly written to support simulation execution on the IRMACS 
cluster. This is a PBS queue based cluster and the ClusterSimulation class was
written to generate queuing scripts from a single configuration file containing
parameter ranges.

This module is in a very early stage, but may still be useful for other 
clusters.

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"


__license__ = "Modified BSD License"

import sys
import os
import numpy
import stat
import glob
import csv

import collections

from nepidemix import simulation
from nepidemix.simulation import Simulation
from nepidemix.utilities import parameterexpander
from nepidemix import exceptions as nepxExceptions
from nepidemix.utilities import NepidemiXConfigParser
# Logging
import logging

logger = logging.getLogger(__name__)




class ClusterSimulation(object):
    """
    Generates a set of different simulations from a parameter range.

    Also has hooks for pre and post processing as well as execution.

    ClusterSimulation expect additional sections in the Simulation 
    configuration file containing cluster/PBS specific information.
    
    It also allows for ranges and lists to be written as option values in the
    normal Simulation section. It will then construct individual Simulation
    compatible configurations for each parameter combination as well as scripts
    to add each simulation to the cluster PBS queue. 

    In adition to the normal `Simulation` configuration sections and options 
    the following cluster-specific are added:

    +------------------+-------------------------------------------------------+
    | Cluster specific sections                                                |
    +------------------+-------------------------------------------------------+
    | Section          | Explanation                                           |
    +==================+=======================================================+
    | ClusterSimConfig | Contains information specific to the cluster project. |
    +------------------+-------------------------------------------------------+
    | PBS 	       | This sections contain information related to writing  |
    |                  | the pbs queue scripts.                                |
    +------------------+-------------------------------------------------------+
    
    And each section has the following options:
    
    +--------------+-----------------------------------------------------------+
    | ClusterSimConfig options                                                 |
    +--------------+-----------------------------------------------------------+
    |Option 	   | Explanation                                               |
    +==============+===========================================================+
    | root_dir 	   | Optional (default value ./). Root directory.              |
    |              | A new directory named after the project will be created   |
    |              | here where all output will be written.                    |
    +--------------+-----------------------------------------------------------+
    | project_name | This is the name of the project. A project directory with |
    |              | this name will be created in the root dir.                |
    +--------------+-----------------------------------------------------------+
    | repetitions  | Optional (default value 1). The number of repetitions     |
    |              | that will be executed for each single parameter           |
    |              | combination.                                              |
    +--------------+-----------------------------------------------------------+


    +--------------+-----------------------------------------------------------+
    | PBS options                                                              |
    +--------------+-----------------------------------------------------------+
    |Option 	   | Explanation                                               |
    +==============+===========================================================+
    | user_email   | Your email address.                                       |
    +--------------+-----------------------------------------------------------+
    | queue_name   | Name of the run queue. Optional.                          |
    +--------------+-----------------------------------------------------------+
    | exec_command | Execution command. The command has one required parameter |
    |              | (the ini file) and one optional (but recommended) being   |
    |              | the number of repetitions.                                |
    +--------------+-----------------------------------------------------------+
    | l_options    | A comma separated list of options, all of these will be   |
    |              | sent with an #PBS -l command. Optional.                   |
    |              | E.g. l_options = mem=1gb, procs=1 will result in the two  |
    |              | statements '#PBS -l mem=1gb' and '#PBS -l procs=1' .      |
    +--------------+-----------------------------------------------------------+

    """

    CFG_SECTION_CLUSTER = 'ClusterSimConfig'
    CFG_SECTION_PBS = 'PBS'

    CFG_PARAM_root_dir = 'root_dir'

    CFG_PARAM_project = 'project_name'
    
    CFG_PARAM_email = 'user_email'
    CFG_PARAM_queue = 'queue_name'
    CFG_PARAM_command = 'exec_command'
    CFG_PARAM_repeats = 'repetitions'
    CFG_PARAM_pbslopts = 'l_options'

    # This section continue info about the run.
    CFG_SECTION_INFO= "Info"
    CFG_PARAM_num_configs = "num_configs"
    CFG_PARAM_repeat_expand = "repeat_expand"
    CFG_PARAM_repeat_call = "repeat_call"
    CFG_PARAM_config_dir_name = "config_dir_base"
    CFG_PARAM_config_base_name = "config_file_base"

    original_config_file_name = 'original_config.ini'
    fileBaseName = 'config'
    confDirName = 'conf_combination'
    deployScriptName =  'deploy.sh'

    def __init__(self, settings = None):
        """
        Initialization.

        Parameters
        ----------
        
        settings : NepidemiXConfigParser, optional
           If given, configure will be automatically called.

        
        """

        # Filter out these sections from the generation and do not let them pass.
        self.exclude_sections = [
            self.CFG_SECTION_CLUSTER, 
            self.CFG_SECTION_PBS, 
            self.CFG_SECTION_INFO
            ]

        # Filter these options from the generation and do not let them pass.
        self.exclude_options = [ (Simulation.CFG_SECTION_SIM, \
                                      Simulation.CFG_PARAM_include_files)
                                 ]
        # Ignore these sections, allowing them to pass on, but do not expand their options.
        # Done for parameter we know to be ranges meant for the simulation.
        self.ignore_sections = []

        # Ignore these options, allowing them to pass on, but do not expand them.
        # Done for parameter we know to be ranges meant for the simulation.
        self.ignore_options = []

        if settings != None:
            self.configure(settings)
    
    def configure(self, settings):
        """
        Configure cluster simulation.
        
        Parameters
        ----------
        
        settings : NepidemiXConfigParser, optional 
           The configuration.

        """

        self.settings = settings

        self.includeFiles = settings.getrange(Simulation.CFG_SECTION_SIM,
                                              Simulation.CFG_PARAM_include_files,
                                              default = [],
                                              add_if_not_existing = False)
            
        if len(self.includeFiles) > 0:
            logger.info("Files {0} will be included.".format(", ".join(self.includeFiles)))
            for fileName in self.includeFiles:
                with open(fileName) as fp:
                    settings.readfp(fp)

        # Parse the main config section
        self.__assertSection(self.CFG_SECTION_CLUSTER)

        self.__assertOptions(self.CFG_SECTION_CLUSTER,
                             self.CFG_PARAM_project)

        if settings.has_option(self.CFG_SECTION_CLUSTER, 
                               self.CFG_PARAM_root_dir):
            self.rootDir = settings.get(self.CFG_SECTION_CLUSTER,
                                        self.CFG_PARAM_root_dir)
        else:
            self.rootDir = './'
        
        self.projectName = settings.get(self.CFG_SECTION_CLUSTER,
                                        self.CFG_PARAM_project)
        self.projectDirPath = self.rootDir +'/'+ self.projectName
        
        self.__assertSection(self.CFG_SECTION_PBS)
        self.__assertOptions(self.CFG_SECTION_PBS,
                             self.CFG_PARAM_email)

        # If there's a command option use that. Otherwise use hardcoded.
        if self.settings.has_option(self.CFG_SECTION_PBS,
                                    self.CFG_PARAM_command):
            self.simprogram = self.settings.get(self.CFG_SECTION_PBS,
                                           self.CFG_PARAM_command)
        else:
            self.simprogram = "nepidemix_runsimulation"

        # Check for repetitions, use if it is not there.
        if self.settings.has_option(self.CFG_SECTION_CLUSTER,
                                    self.CFG_PARAM_repeats):
            self.reps = self.settings.getint(self.CFG_SECTION_CLUSTER,
                                             self.CFG_PARAM_repeats)
        else:
            self.reps = 1


        # Add info section
        if not self.settings.has_section(self.CFG_SECTION_INFO):
            self.settings.add_section(self.CFG_SECTION_INFO)


    def createSimulationConfigs(self):
        """
        Tailor build individual configurations for each simulation case.
        """
        # Go through all settings options. Those not belonging to this
        # class is assumed to belong to the program we want to deploy.
        logger.info("Building parameter lists...")
        paramRangeList, varOptList \
            = buildParamRangeList(self.settings,
                                  excludeSections = self.exclude_sections,
                                  excludeOptions = self.exclude_options,
                                  ignoreSections = self.ignore_sections,
                                  ignoreOptions = self.ignore_options)

        logger.info("Creating project directory at '{0}'".format(self.projectDirPath))
        os.makedirs(self.projectDirPath)
        ncalls = 0
        deployScriptName =  self.projectDirPath +'/' + self.deployScriptName
        logger.info("Creating deploy script '{0}'".format(deployScriptName))
        deployScriptFp = open(deployScriptName, 'w')
        deployScriptFp.write("""
#!/bin/bash
# This script is automatically generated.
# Running it will submit all generated PBS jobs to the queue.
""")
        for ddict, cpath in paramsPaths(self.projectDirPath, 
                                        paramRangeList, self.confDirName,
                                        excludeSections = self.exclude_sections, 
                                        excludeOptions = self.exclude_options,
                                        ignoreSections = self.ignore_sections,
                                        ignoreOptions = self.ignore_options):
            cp = NepidemiXConfigParser()
            os.makedirs(cpath, 0750)
            
            
            fname = cpath + "/{0}_{1}".format(self.fileBaseName, ncalls)
            # Write ini file.
            with open(fname+'.ini', 'w') as fp:
                for (sec, opt), val in ddict.items():
                    if not cp.has_section(sec):
                        cp.add_section(sec)
                    cp.set(sec,opt,val)
                cp.write(fp)
        
            queue_name = self.settings.get(self.CFG_SECTION_PBS,
                                           self.CFG_PARAM_queue,
                                           default = '')
            if len(queue_name) < 1:
                queue_string = ""
            else:
                queue_string ="#PBS -q {queue_name}".format(queue_name=queue_name)

            # Write PBS file.
            with open(fname+'.pbs', 'w') as fp:
                # Header, email and output.
                fp.write("""
#!/bin/bash
#PBS -N {job_name}
{queue_string}
#PBS -M {user_email}
#PBS -m bae
#PBS -j oe
#PBS -o {path_to_log}
#PBS -e {path_to_elog}
""".format(job_name = self.projectName + "_{0}".format(ncalls),
           queue_string = queue_string,
           user_email = self.settings.get(self.CFG_SECTION_PBS,
                                          self.CFG_PARAM_email),
           path_to_log = fname+'.log',
           path_to_elog = fname+'_error.log'))

                # Write -l options.
                
                if self.settings.has_option(self.CFG_SECTION_PBS,
                                            self.CFG_PARAM_pbslopts) == True:
                    for los in self.settings.\
                            parseTuple(self.settings.get(self.CFG_SECTION_PBS,
                                                         self.CFG_PARAM_pbslopts)):
                        fp.write("#PBS -l {0}\n".format(los))


                # Write the execution commands.
                fp.write("""
cd {work_dir}
{command}
""".format(work_dir = cpath,
           command = self.simprogram+" {0}.ini {1}".format(fname, self.reps)))
            
            # Add a command to submit the pbs file to our deployment script.
            deployScriptFp.write("qsub {0}.pbs; sleep 0.2\n".format(fname))
            ncalls = ncalls + 1

        deployScriptFp.close()
        # Make deploy script executable for user.
        os.chmod(deployScriptName, 0744)



        self.settings.set(self.CFG_SECTION_INFO, self.CFG_PARAM_num_configs, 
                          ncalls)
        self.settings.set(self.CFG_SECTION_INFO, self.CFG_PARAM_config_base_name, 
                          self.fileBaseName)
        self.settings.set(self.CFG_SECTION_INFO, self.CFG_PARAM_config_dir_name, 
                          self.confDirName)


        # Write the (extended) settings backt to file so that the project
        # is self contained in some way.
        with open(self.projectDirPath + '/{0}'.format(self.original_config_file_name), 'w') as ofp:
            self.settings.write(ofp)
        logger.info("Done, created {0} individual configurations to be repeated {1} times."\
                        .format(ncalls, self.reps))
   
        

            
    def __assertSection(self,section):
        """
        Check if the class config has a specific section. 
        Raise error otherwise.

        Parameters
        ----------

        section : str
           Name of section.

        """
        if not self.settings.has_section(section):
            emsg = "Missing mandatory configuration section '{0}'"\
                .format(section)
            logger.error(emsg)
            raise nepxExceptions.NepidemiXBaseException(emsg)

    def __assertOptions(self,section, *args):
        """
        Assert that a given section in the config has all the listed options. 
        Raise error otherwise.

        Parameters
        ----------

        section : str
           Name of section.

        *args : special
           All the remaining arguments are considered option names.

        """
        missingOptions = []
        for opt in args:
            if not self.settings.has_option(section, opt):
                missingOptions.append(opt)
        if len(missingOptions) > 0:
            emsg = "Missing mandatory configuration option(s) in section '{0}': {1}"\
                .format(section, ','.join(missingOptions))
            logger.error(emsg)
            raise nepxExceptions.NepidemiXBaseException(emsg)

def buildParamRangeList(settings, 
                        excludeSections  = [], excludeOptions = [],
                        ignoreSections = [], ignoreOptions = []):
    """
    Building the parameter range list from a NepidemiXConfigParser object.
    
    The list is a tuple of the form ( (section, option), rvals ) where rvals is on the
    form returned by parseRange.
    
    Parameters
    ----------

    settings : NepidemiXConfigParser
       The settings object.

    excludeSections : array_like
       List of section names to exclude. 
       I.e. their content won't be transferred to the result.

    excludeOptions : array_like
       List of (section, option) pairs of names to exclude. 
       I.e. their content won't be transferred to the result.

    ignoreSections : array_like
       List of section names not to expand.
       Nothing in these sections will be expanded even if they contain ranges
       but their values will still be moved to the result.

    ignoreOptions : array_like
       List of (section, option) pairs not to expand.
       These options will not be expanded even if they contain ranges
       but their values will still be moved to the resulting list.

    Returns
    -------
    
    paramRangeList : array_like
       List of parameter ranges.

    varOptList : array_like
       List of (secton, option) keys.

    """
    paramRangeList = []
    varOptList = []
    for sect in settings.sections():
        if sect not in excludeSections:
            for optName, optValue in settings.items(sect):
                if (sect, optName) not in excludeOptions:
                    if (sect not in ignoreSections) \
                            and ((sect, optName) not in ignoreOptions):
                        rvals = settings.parseRange(optValue)
                    else:
                        rvals = [optValue]

                    if len(rvals) > 1:
                           varOptList.append((sect,optName)) 
                    paramRangeList.append(((sect, optName),
                                           rvals))

    return paramRangeList, varOptList




def findVaryingParameters(pConfig,
                          ignoreSections = [], 
                          ignoreOptions = []):
    """
    Find varying variables in a config file.
    
    Parameters
    ----------
    
    pConfig : NepidemiXConfigParser
       The settings as a NepidemiXConfigParser compatible object.

    ignoreSections : array_like
       List of section names to exclude when working with congigurations.
       Nothing in these sections will be expanded even if they contain ranges
       but their values will still be moved to the result.

    ignoreOptions : array_like
       List of (section, option) pairs not to count.
       These options will not be expanded even if they contain ranges
       but their values will still be moved to the resulting list.    

    Returns
    -------
    
    pd : dict
       A dictionary on the form (<section>,<parameter>):[<value 1>, ... <value n>]

    """
    pd = collections.OrderedDict()
    for sec in pConfig.sections():
        if sec not in ignoreOptions:
            for opt in pConfig.options(sec):
                if (sec, opt) not in ignoreOptions:
                    val = pConfig.getrange(sec,opt)
                    if len(val) > 1:
                        pd[(sec,opt)] = val
    return pd
                             

def paramsPaths(projectDir, paramRangeList = None, confDirName=None,
                excludeSections  = [], excludeOptions = [],
                ignoreSections = [], ignoreOptions = []):
    """
    Generator giving all parameters and paths in a project.

    Parameters
    ----------

    projectDir : str
       Project directory path as string.
       
    paramRangeList : array_like
       Parameter range list on the form described in parameterexpander.

    confDirName : str
       Base name of the configuration directories as a string.

    paramRangeList : array_like, optional
       List of parameter ranges. If left out together with `confDirName` the 
       function assumes that this is an initialized project directory and 
       attemtps to load the values from the ini file.

    confDirName : array_like, optional
       List of (secton, option) keys. If left out together with `paramRangeList`
       the function assumes that this is an initialized project directory and
       attemtps to load the values from the ini file.

    excludeSections : array_like
       List of section names to exclude when working with congigurations.
       I.e. their content won't be transferred to the result.

    excludeOptions : array_like
       List of (section, option) pairs of names to exclude. 
       I.e. their content won't be transferred to the result.

    ignoreSections : array_like
       List of section names to exclude when working with congigurations.
       Nothing in these sections will be expanded even if they contain ranges
       but their values will still be moved to the result.

    ignoreOptions : array_like
       List of (section, option) pairs not to expand when working with
       configuration.
       These options will not be expanded even if they contain ranges
       but their values will still be moved to the resulting list.

    Yields
    ------

    param : dict
       A dictionary of the current parameter names and values.

    path : str
       The path to the corresponding directory in the project path as a string.

    """


    # Check so that the directory exists
    if not os.path.isdir(projectDir):
        raise IOError("Project directory '{0}' does not exist.".format(projectDir))
    if confDirName == None:
        # Read configuration.
        cp = projectConfig(projectDir)

        # Find out what the config directory name is
        if cp.has_option(ClusterSimulation.CFG_SECTION_INFO, ClusterSimulation.CFG_PARAM_config_dir_name):
            confDirName = cp.get(ClusterSimulation.CFG_SECTION_INFO, ClusterSimulation.CFG_PARAM_config_dir_name)
        else:
            # This is here for backward compatibility reasons.
            confDirName = 'conf_combination'

    if paramRangeList == None:
        # Construct paramRangeList
        paramRangeList, varOptList = \
            buildParamRangeList(cp,  
                                excludeSections = excludeSections,
                                excludeOptions = excludeOptions,
                                ignoreSections = ignoreSections,
                                ignoreOptions = ignoreOptions)

    n = 0
    for param in parameterexpander.combineParameters(paramRangeList):
        cpath = "{0}/{1}_{2}".format(projectDir, confDirName,n)
        yield param, cpath
        n = n + 1



def projectConfig(projectDir):
    """
    Return the configuration object representing the project config.

    Parameters
    ----------

    projectDir :str
       Project directory path as string.

    Returns
    -------

    cp : NepidemiXConfigParser
       A configuration object representing the project directory configuration.

    """
    # Check so that the directory exists
    if not os.path.isdir(projectDir):
        raise IOError("Project directory '{0}' does not exist.".format(projectDir))
    # Read the Cluster simulation
    cp = NepidemiXConfigParser()
    with open(projectDir +'/' + ClusterSimulation.original_config_file_name, 'r') as fp:
        cp.readfp(fp)
    return cp



def projectContent(projectDir, excludeSections = [], excludeOptions = [],
                   ignoreSections = [], ignoreOptions = []):
    """
    Generator giving the config for each individual parameter combination and
    the list of files in that specific configuration directory.
    

    Parameters
    ----------

    projectDir : str
       Project directory path as string.
    
    excludeSections : array_like
       List of section names to exclude when working with congigurations.
       I.e. their content won't be transferred to the result.

    excludeOptions : array_like
       List of (section, option) pairs of names to exclude. 
       I.e. their content won't be transferred to the result.

    ignoreSections : array_like
       List of section names to exclude when working with congigurations.
       Nothing in these sections will be expanded even if they contain ranges
       but their values will still be moved to the result.

    ignoreOptions : array_like
       List of (section, option) pairs not to expand when working with
       configuration.
       These options will not be expanded even if they contain ranges
       but their values will still be moved to the resulting list.

  
    Yields
    ------

    params : dict
       The parameters as a dictionary.

    fileList : list
       The list of all files.



    """
    # Check so that the directory exists
    if not os.path.isdir(projectDir):
        raise IOError("Project directory '{0}' does not exist.".format(projectDir))

    # Read configuration.
    cp = projectConfig(projectDir)

    # Find out what the config directory name is
    if cp.has_option(ClusterSimulation.CFG_SECTION_INFO, ClusterSimulation.CFG_PARAM_config_dir_name):
        confDirName = cp.get(ClusterSimulation.CFG_SECTION_INFO, ClusterSimulation.CFG_PARAM_config_dir_name)
    else:
        # This is here for backward compatibility reasons.
        confDirName = 'conf_combination'
    if cp.has_option(ClusterSimulation.CFG_SECTION_INFO, ClusterSimulation.CFG_PARAM_config_base_name):
        confBaseName = cp.get(ClusterSimulation.CFG_SECTION_INFO, ClusterSimulation.CFG_PARAM_config_base_name)
    else:
        # This is here for backward compatibility reasons.
        confBaseName = 'config'

    # Construct paramRangeList
    paramRangeList, varOptList \
        = buildParamRangeList(cp,  
                              excludeSections = excludeSections,
                              excludeOptions = excludeOptions,
                              ignoreSections = ignoreSections,
                              ignoreOptions = ignoreOptions)

    # Loop
    for params, cpath in paramsPaths(projectDir, paramRangeList, confDirName, 
                                     excludeSections = excludeSections, excludeOptions = excludeOptions, 
                                     ignoreSections = ignoreSections, ignoreOptions = ignoreOptions):
        # File base name (from global config)
        fileBaseName = cp.get(Simulation.CFG_SECTION_OUTPT,
                              Simulation.CFG_PARAM_baseFileName)

        # Read all configs.
        cpInd = None
        # Try reading the csv file.
        data = None            
        wildFile = cpath+'/'+cp.get(Simulation.CFG_SECTION_OUTPT,
                                    Simulation.CFG_PARAM_baseFileName)+'*'
        fileList = glob.glob(wildFile)
        yield params, fileList
