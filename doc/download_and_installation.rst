
Downloading and installing NepidemiX
====================================

Prerequisites
-------------

NepidemiX is written in Python and uses functions in some third party Python packages (most notably NetworkX and numpy). You Will need these installed on your system before you can run NepidemiX. See the lists below for details.

Required software
~~~~~~~~~~~~~~~~~

* Python 2.7 [ http://www.python.org/download ]
   NepidemiX was written for python 2.7 (at the time when development started some of the third party packages did not support Python 3), 2.6 should work as well. Python 3 is currently not officially supported, but we are working on it.

* numpy [ http://numpy.scipy.org/ ]
   Download the latest version for your system and follow the installation instructions. Numpy can also be installed as part of the larger scipy package ( http://www.scipy.org ) which brings many additional features.

* NetworkX [ http://networkx.lanl.gov/ ]
   Download the latest version and follow the installation instructions for your system.



For developers
~~~~~~~~~~~~~~

If you want to get NepidemiX directly from the development repository or generate this documentation you will in addition need.

* git [ http://git-scm.com/ ]
   A powerful and versatile version control system

* sphinx [ http://sphinx.pocoo.org/ ]
   A python documentation system. Needed if you want to generate the documentation.

Download
--------

You can either download a release version of NepidemiX below or you can get the software directly from `our development repository on github <https://github.com/impact-hiv/NepidemiX>`_ .

Releases
~~~~~~~~

We release the software at certain stages of development, and try to document the changes between each, making sure that the documentation is up to date et c. You can find the latest release below.

* NepidemiX 0.1 

Save the file on your system, unpack it and follow the Installation_ instructions below.

Development repository
~~~~~~~~~~~~~~~~~~~~~~

`NepidemiX on github <https://github.com/impact-hiv/NepidemiX>`_

Our development repository contains the working version of the code. By cloning this you can make sure that you will always have the latest version of the software. However, while this code may contain bug fixes and new features, it may also be unstable and not fully documented.

To clone a copy of the repository directly you can run the following::

   >> git clone git://github.com/impact-hiv/NepidemiX.git


Installation
------------

To install, open a terminal in your NepidemiX directory and run the setup script as::

   >> python setup.py install

Notes
~~~~~

* You may need to run the above with administrator privileges or as super-user.

* Advanced users: If you have several python versions installed on your system make sure that you run the right python (e.g. python2, python3).
