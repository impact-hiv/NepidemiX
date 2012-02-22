Python SIJR model
=================

The SIJR model is non-standard, and further explained in the :ref:`tutorial`. Briefly it defines an extra super-infectious stage to the SIR model whereby any node in the J-state in addition to acting as a normal infecting node also creates a mean field over the whole population, ignoring network structure, and influencing the probability of infecting all susceptible nodes. 

The python example below is not the recommended way of implementing such a structure but was included in the :ref:`tutorial` as an example.


SIJR process class
------------------

.. literalinclude:: modules/extended_SIR.py
   :pyobject: SIJRProcess


SIJR simulation configuration
-----------------------------

.. literalinclude:: conf/SIJR_example.ini
