"""
ParameterExpander
=================

This module provides functionality to expand a range of parameter for multiple
function calls.

Each parameter can be given one or more value. The expander then proceeds to
create a unique call of the provided function for each combination of value.

"""

__author__ = "Lukas Ahrenberg (lukas@ahrenberg.se)"

__license__ = "Modified BSD License"

__all__ = ["combineParameters", "repeatParameters"]

import time

from collections import OrderedDict


def combineParameters(paramRangeList, singleParamsDict = OrderedDict()):
    """
    Generator for each combination of parameters. Will yield a dictionary of
    individual combinations.
    
    Parameters
    ----------
    
    paramRangeList : list
       List of tuples, where the first tuple value is the name the parameter and
       the second is a list or vector with parameter values. 
       Form: [ ( parameterName_1, [ p_11, p_12, ... p_1n]),
       ( parameterName_2, [ p_21, p_22, ... p_2k]),
       ...
       ( parameterName_m, [ p_m1, p_m2, ... p_ml]) ]
       Example: [("a", [1,2]), ("b". [5,6])]

    singleParamsDict : dict, optional
       This is a dictionary of single name:parameter pairs. Default value is an
       empty dictionary. Used recursively.

    """
    if paramRangeList !=[]:
        pname, prange = paramRangeList[0]
        for val in prange:
            singleParamsDict[pname] = val
            for comb in combineParameters(paramRangeList[1:], singleParamsDict):
                yield comb
    else:
        yield singleParamsDict

def repeatParameters(execFunc, times, singleParamsDict, sendDict = False):
    """
    Convenience function executing a function a number of times with the same
    parameter list.
    
    Parameters
    ----------

    execFunc : function
       Function to execute

    times : int
       Number of times to repeat execution.

    singleParamsDict : dict
       Dictionary of parameter name:value pairs. Will be used to call execFunc 
       in a **kwargs style.

    sendDict : bool, optional
       Flag indicating if the dictionary of parameters should be submitted to 
       execFunc instead of the parameters themselves.
       Default value: False

    Yields
    ------

    Result of each consecutive execution.

    """
    for n in range(times):
        if sendDict == True:
            yield execFunc(singleParamsDict)
        else:
            yield execFunc(**singleParamsDict)


