"""
=======
Logging
=======

Provides a convenience function to set up logging.

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

import logging
import sys

# Set up Logging
logger = logging.getLogger(__name__)


def setUpLogging():
    """
    Set up root logger.

    """
    rootLogger = logging.getLogger()
    # We want to log all from DEBUG and up.
    rootLogger.setLevel(logging.DEBUG)
    loggingFormat = logging.Formatter(
        "%(asctime)s. - %(name)s - %(levelname)s - %(message)s")
    # Send warnings, errors and critical to stderr
    logStdErrHandler = logging.StreamHandler(sys.stderr);
    logStdErrHandler.setFormatter(loggingFormat)
    # Ignore everything below WARNING level.
    logStdErrHandler.setLevel(logging.WARNING)
    rootLogger.addHandler(logStdErrHandler)
    # Send debug and info (all below WARNING level) to stdout.
    logStdOutHandler = logging.StreamHandler(sys.stdout);
    logStdOutHandler.setFormatter(loggingFormat)
    logStdOutFilter = _LogInRangeFilter()
    # Ignore anything outside this range.
    logStdOutFilter.setRange(logging.DEBUG, logging.WARNING)
    logStdOutHandler.addFilter(logStdOutFilter)
    rootLogger.addHandler(logStdOutHandler)


def configureLogging(level):
    """
    Configure logging from a NepidemiXConfigParser object.

    Parameters
    ----------

    level
       The debugging level. Values:
          * DEBUG - sets to debug level.
          * INFO - sets to info level.
          * WARN - sets to warning level.
          * SILENT - Disables ALL logging.

    """
    
    if level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif level == "INFO":
        logging.getLogger().setLevel(logging.INFO)
    elif level == "WARN":
        logging.getLogger().setLevel(logging.WARNING)
    elif level == "SILENT":
        logging.disable(100)
    else:
        logger.error("Unrecognized message level '{0}'".format(level))
    logger.info("Message level set to: " +level)


# The python logging facility only provide a lower bound for the logs.
# Create filter to check for a range.
class _LogInRangeFilter:
    """
    Class used as filter in the logging framework. 
    Passes messages with lowLevel<=level<highLevel.
    
    """
    def __init__(self):
        """ 
        Initialize. Set default levels.

        """  
        self.lowLevel = logging.WARNING
        self.highLevel = logging.CRITICAL

    def setRange(self, lowLevel, highLevel):
        """
        Set range to given levels. 

        """  
        self.lowLevel = lowLevel
        self.highLevel = highLevel

    def filter(self, record):
        """ 
        The filter method. 

        Parameters
        ----------
        
        record : record
           Log record

        Returns
        -------
        
        keep : bool
           True if record should be kept, else False.
        
        """  
        if record.levelno >= self.lowLevel and record.levelno < self.highLevel:
            return True
        return False

