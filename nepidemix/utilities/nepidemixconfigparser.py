"""
NepidemiX configuration parser
==============================

Python configuration parser compatible with some additional functionality such as 
guaranteed ordering of items and type casting.

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

__all__ = ["NepidemiXConfigParser"]

import numpy
import re


import collections

# Logging
import logging

logger = logging.getLogger(__name__)

from ..exceptions import NepidemiXBaseException

class NepidemiXConfigParser(object):
    """
    NepidemiX ini-file reader.

    Written to have similar interface as Python 2.x RawConfigParser, but with 
    some added improvements, and most importantly using collections.OrderedDict
    for the option, value pairs within a section. This will guarantee that 
    options are presented by the Parser in the same order as they are listed in
    the file. There are also other improvements to the interface used by 
    ConfigParser. Among them are the option of default values for the 
    get-methods, as well as general data types, and parsing of special ranges 
    et c.

    The options and sections in the ini files are case
    sensitive.
    """
    def __init__(self):
        """
        Init method.

        """
        self.sectionDict = collections.OrderedDict()

    def read(self, fileName):
        """ 
        Read a file. 
    
        Parameters
        ----------

        fileName : str
           File name as string.

        """
        with open(fileName, 'r') as fp:
            self.readfp(fp)
            
    def readfp(self, fp):
        """ 
        Read a file. 

        Parameters
        ----------

        fp : File pointer

        """
        currentSection = None
        currentOptionsList = None
        for line in fp:
            # Split off comments starting with '#'
            # Strip from white-spaces at the ends.
            l = line.strip().split('#')[0].strip()
            if len(l) > 0:
                # Check for section.
                # The reg exp searches for [ ] at the start of the line
                # The name must start with an alpha-num but can contain spaces (is this wise?)
                m = re.search('(^\[\w[\w\s]+\])', l)
                if m != None:
                    # Happily ignore more than one name on a line.
                    currentSection = m.group(0).strip('[').strip(']')
                    if not self.sectionDict.has_key(currentSection):
                        self.sectionDict[currentSection] = []
                    currentOptionsList = self.sectionDict[currentSection]
 #                   logger.debug("[{0}]".format(currentSection))
                else:
                    # Check so that we have a current section. 
                    # If not someone is writing options in the file without
                    # first submitting a section.
                    if currentSection == None:
                        logger.error("An ini file option must be within a section. No section provided. Ignoring line '{0}'."\
                                         .format(l))
                    else:
                        # Split the string at either = .
                        ll = l.split('=',1)
                        if len(ll) < 2:
                            logger.error("Warning only option {0} found, no value. Setting to None."\
                                                 .format(l))
                            val = None
                        else:
                            val = ll[1].strip()
                        opt = ll[0].strip()
                        currentOptionsList.append((opt,val))


    def write(self, fileobject):
        """
        Write file to file object.

        Writes the configuration to a file.

        Parameters
        ----------

        fileobject : file
           A file object opened with `open`.

        """
        for sect, optList in self.sectionDict.iteritems():
            fileobject.write("[{0}]\n".format(sect))
            for opt,val in self.sectionDict[sect]:
                fileobject.write("{0} = {1}\n".format(str(opt), str(val)))
            fileobject.write("\n")

    def sections(self):
        """
        Return all section names.

        Returns
        -------
        
        sections :  array_like
           List of all section names.
        
        """
        return self.sectionDict.keys()

    def options(self, section):
        """
        Return all options in a section.
        
        Parameters
        ----------
        
        section : str
           The section.

        Returns
        -------
        
        options : array_like
           List of all option names in `section`.
        
        """
        return [opt for opt,val in self.sectionDict[section]]

    def has_section(self, section):
        """
        Returns true if the parser has the section.

        Parameters
        ----------
        
        section : str
           The section.

        Returns
        -------
        
        section :  bool
           True if the parser has `section`.

        """
        return section in self.sectionDict.keys()
    
    def has_option(self, section, option):
        """
        Returns true if the parser has the option in the section.

        Parameters
        ----------
        
        section : str
           The section.

        option : str
           The option.

        Returns
        -------

        found : bool
          True if the parser has `section` and this include `option`.
        
        """
        if not self.has_section(section):
            return False
        found = False
        for opt,val in self.sectionDict[section]:
            if opt == option:
                found = True
                break
        return found
            
    def items(self, section):
        """
        Return the list of (option,value) pair from a specific section.

        Parameters
        ----------

        section : str 
           The section.

        Returns
        -------

        optionvalues : array_like
           List of all (option, value) tuples in `section`.

        """
        return self.sectionDict.get(section,[])

    def add_section(self, section):
        """
        Add a section, if it does not already exist.

        Parameters
        ----------

        section : str
           Name of the section.

        """
        if not self.has_section(section):
            self.sectionDict[section] = []

    def set(self, section, option, value, createSection = True):
        """
        Sets the option in section to value.
        Creates a missing section if createSection is True (default).

        Parameters
        ----------

        section : str
           The section.

        option : str
           The option.

        value : str
           The value to set.

        createSection : bool, optional
           If set to True missing sections will be created. If False an 
           exception will be raised.

        """
        if not self.has_section(section):
            if createSection == False:
                raise NepidemiXBaseException(section)
            else:
                self.sectionDict[section] = []

        self.sectionDict[section].append((option,value))


    def get(self, section, option, default=None, add_if_not_existing=True, dtype=str):
        """
        Get a value from an option in a section.
        Ability to cast to a specific data type; return a default value if the 
        option does not exist, as well as adding the value to the config.
        
        Parameters
        ----------

        section :str
           The config section.

        option : str
           The config option.

        default : special, optional
           If None an exception will be raised if `option` does not exist. If 
           not None, the value of `default` will be returned and no exception 
           raised. Default - None.

        add_if_not_existing : bool, optional
           If this is True, the option does not exist and` default` != None, the
           option will be created and set to the value of default.
           
        dtype : special
           The read string will be cast to this data type. Default str.

        
        Returns
        -------

        val : special
          The value of `option` casted to `dtype`.

        """
        # Linear search for right option.
        found = False
        for opt,val in self.sectionDict[section]:
            if opt == option:
                found = True
                break
        if not found:
            if default != None:
                val = default
                if add_if_not_existing == True:
                    self.set(section, option, default)
            else:
                raise NepidemiXBaseException(option)
        return dtype(val)

    def getint(self, section, option, default=None, add_if_not_existing=True):
        """
        Get an integer value.

        Parameters
        ----------

        section :str
           The config section.

        option : str
           The config option.

        default : special, optional
           If None an exception will be raised if `option` does not exist. If 
           not None, the value of `default` will be returned and no exception 
           raised. Default - None.

        add_if_not_existing : bool, optional
           If this is True, the option does not exist and` default` != None, the
           option will be created and set to the value of default.

        Returns
        -------

        val : int
          The value of `option` casted to int.

        """
        return self.get(section, option, default, add_if_not_existing, dtype=int)
    
    def getfloat(self, section, option, default=None, add_if_not_existing=True):
        """
        Get a float value.

        Parameters
        ----------

        section :str
           The config section.

        option : str
           The config option.

        default : special, optional
           If None an exception will be raised if `option` does not exist. If 
           not None, the value of `default` will be returned and no exception 
           raised. Default - None.

        add_if_not_existing : bool, optional
           If this is True, the option does not exist and` default` != None, the
           option will be created and set to the value of default.

        Returns
        -------

        val : float
          The value of `option` casted to float.

        """
        return self.get(section, option, default, add_if_not_existing, dtype=float)

    def getboolean(self, section, option, default=None, add_if_not_existing=True):
        """
        Get a boolean value.

        Parameters
        ----------

        section :str
           The config section.

        option : str
           The config option.

        default : special, optional
           If None an exception will be raised if `option` does not exist. If 
           not None, the value of `default` will be returned and no exception 
           raised. Default - None.

        add_if_not_existing : bool, optional
           If this is True, the option does not exist and` default` != None, the
           option will be created and set to the value of default.

        Returns
        -------

        val : bool
          The value of `option` casted to bool.

        """
        def boolmap(b):
            return b.lower() not in ['0','no', 'off', 'false']

        if default != None and default == True:
            default = 'true'
        if default != None and default == False:
            default = 'false'

        return self.get(section, option, default , add_if_not_existing, dtype=boolmap)

    
    def getrange(self, section, option, dtype=str, default=None):
        """
        Create a range of values from option string.

        The valid formats of the string are

           * A single value.
           * A comma-separated list of values
           * The form <first>:<step>:<last>

        The function create an array containing the values, and also generate 
        the range in the last case.

        Thus the value of the option should be on the form:
        
           <option> = <value>
        
           <option> = <value>, <value>, <value>, ..., <value>
        
           <option> = <number>:<number>:<number>


        Parameters
        ----------
        
        section :str
           The config section.

        option : str
           The config option.

        default : special, optional
           If None an exception will be raised if `option` does not exist. If 
           not None, the value of `default` will be returned and no exception 
           raised. Default - None.

        dtype : special, optional
           The datatype of the returned numpy array. Default: str .


        Returns
        -------

        rangeArray : numpy.array
           The method returns a numpy array contining the values in the string 
           either the single value, the list of values, or the range from first 
           (inclusive) to last (exclusive) by the step step.

        """
        # Get the option as a string.
        rstring = self.get(section, option, default = "", dtype=str)
        # Check if we got the empty string. Then return default.
        if rstring == "":
            return default
        # Otherwise parse the string.
        return self.parseRange(rstring, dtype)


    def parseRange(self, rstring, dtype=str):
        """
        Create a range of values from a string.

        Utility method.

        The valid formats of the string are
           * A single value.
           * A comma separated list of values
           * The form <first>:<step>:<last>

        The function create an array containing the values, and also generate 
        the range in the last case.

        Parameters
        ----------
        
        rstring : str 
           A string on the form:
           <value>, or <value>, <value>, <value>, ..., <value>, or <number>:<number>:<number>

        dtype : special, optional
           Datatype used for the numpy array. Default: str.

        Returns
        -------

        retval : numpy.array
           The method returns a numpy array contining the values in the string 
           either the single value, the list of values, or the range from first
           (inclusive) to last (exclusive) by the step step.

        """ 
        retval = None
        if rstring.find(':') > -1:
            # Check if there's a ':' in that case we assume it is a range.
            stps = rstring.split(':')
            if len(stps) != 3:
                # We need exactly 3 numbers, print error otherwise.
                msg = "A range must be on the form <number>:<number>:<number>"
                logger.error(msg)
            else:
                # If all of the values has int-type use that,
                # otherwise it has to be float.
                # Not best way of checking, but the only useful right 
                # now as there's no type support in the ini files.
                try:
                    rstart = int(stps[0].strip())
                    rstep = int(stps[1].strip())
                    rend = int(stps[2].strip())
                except ValueError:
                    rstart = float(stps[0].strip())
                    rstep = float(stps[1].strip())
                    rend = float(stps[2].strip())
                retval = numpy.arange(rstart, rend, rstep)
        else:
            # In this case we should have a single value, or an comma-
            # separated list of numbers.
            # Create the list of numbers.
            retval = numpy.array([n.strip() for n in rstring.split(',')],dtype=dtype)
#        logger.debug("Created array: {0}".format(retval))
            
        return retval

    def parseTuple(self, lstring, dtype=str):
        """
        Create a tuple from a comma separated string.

        Utility method.

        Parameters
        ----------
        
        lstring : str
           The string.
        
        dtype : special, optional
           The individual elements of the tuple will be cast to this type.

        Returns
        -------
        
        ttuple : tuple
           A tuple containing the elements of the comma-separated string.
        
        """
        return tuple([dtype(n.strip()) for n in lstring.split(',')])

    def parseMapping(self, mapStr, dtype=str):
        """
        Parse a mapping string on the form src->dest.

        Utility method.
        
        Parameters
        ----------

        mapStr : str
           String on the form  <src> -> <dest>

        dtype : special, optional
           Before returning the source and dest objects will be casted using 
           this function. Default: str.

        Returns
        -------

        src : str
           Left of the '->' operator.
        
        dst : str
           Right of the '->' operator.

        """
        sp = mapStr.split('->')
        
        if len(sp) != 2:
            err = "Could not parse mapping {0}. Mapping must be on the form <src> -> <dst>."\
                .format(mapStr)
            logger.error(err)
            raise NepidemiXBaseException(err)
        return (dtype(sp[0].strip()), dtype(sp[1].strip()))


    def evaluateSection(self, section):
        """
        Interpretate option values in a section as expressions, evaluates them, 
        and return a the results as a dictionary.
        
        The options are evaluated in order, so that already defined options can
        be used in the expressions for sequential ones.
       
        Parameters
        ----------

        section : str
           Name of the section.
        
        Returns
        -------

        resDict : dict
           A dictionary with options as keys and the result from evaluation as 
           values.


        """
        resDict = collections.OrderedDict()
        for opt in self.options(section):
            val = self.get(section, opt)
            gDict = resDict.copy()
            try:
                resDict[opt] = eval(val, gDict)
            except NameError:
                resDict[opt] = val
            except SyntaxError:
                logger.info("Don't know how to evaluate '{0}' interpreting as string."\
                                .format(val))
                resDict[opt] = val
        return resDict
