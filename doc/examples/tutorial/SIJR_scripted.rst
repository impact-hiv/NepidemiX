Scripted SIJR model
===================

The SIJR model is non-standard, and further explained in the :ref:`tutorial`. Briefly it defines an extra super-infectious stage to the SIR model whereby any node in the J-state in addition to acting as a normal infecting node also creates a mean field over the whole population, ignoring network structure, and influencing the probability of infecting all susceptible nodes. 


SIJR process definition
-----------------------

.. literalinclude:: conf/SIJR_scripted_pdef.ini


SIJR simulation configuration
-----------------------------

.. literalinclude:: conf/SIJR_scripted_example.ini
