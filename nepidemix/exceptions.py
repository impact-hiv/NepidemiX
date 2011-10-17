"""
==========
Exceptions
==========

NepidemiX project exceptions.

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

__all__ = ["NepidemiXBaseException"]

class NepidemiXBaseException(Exception):
    """
    Generic exception for the Network Model class.
    
    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)
