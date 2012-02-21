
"""
Implementation of a basic linked counter class. Counters linked to each others perform
the incremental/decremental arithmetic operations += and -= in unison.

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

__all__ = ["LinkedCounter"]

class LinkedCounter(object):
    """
    This describes a counter class having increase and decrease operators that is
    linked to other linked counters and they get increased/decreased at the same
    time (but can have different initial values).

    Examples
    --------

    If linked counter A = LinkedCounter(1) and B = LinkedCounter(2, [A]) then
    setting A+=1, means that A == 2, and B == 3. However, B+=1 next will lead to 
    B == 4, while A == 2. The links are therefore directional.

    """
    def __init__(self, initval, listenerList = []):
        """

        Parameters
        ----------
        
        initval : value
           Initial value.

        listenerList : list
           List of other objects that will be increased when this LinkedCounter is.

        """
        self.counter = initval
        self.linkedCounters = []
        for l in listenerList:
            self.linkedCounters.append(l)

    def set(self, value, broadcast = True):
        """
        Set the linked object to a value.
        
        Parameters
        ----------
        
        value: int
           The value.

        broadcast: bool, optional
           If true the value will be broadcast to all linked counters.

        """
        self.counter = value
        if broadcast == True:
            for c in self.linkedCounters:
                c.counter = value
        return self

    def __repr__(self):
        return "LinkedCounter({0}, [{1}])".format(self.counter, self.linkedCounters)

    def __str__(self):
        return str(self.counter)

    def __int__(self):
        return int(self.counter)

    def __lt__(self, other):
        return self.counter < other

    def __le__(self, other):
        return self.counter <= other

    def __eq__(self, other):
        return self.counter == other

    def __ne__(self, other):
        return self.counter != other
 
    def __gt__(self, other):
        return self.counter > other

    def __ge__(self, other):
        return self.counter >= other

    def __iadd__(self, other):
        self.counter += other
        for c in self.linkedCounters:
            c.counter += other
        return self

    def __isub__(self, other):
        self.counter -= other
        for c in self.linkedCounters:
            c.counter -= other
        return self

    def __add__(self, other):
        return self.counter + other

    def __sub__(self, other):
        return self.counter - other

    def __mul__(self,other):
        return self.counter * other

    def __div__(self,other):
        return self.counter / other
