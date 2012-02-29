"""
NepidemiX - simulation of contact processes on networks.

NeipdemiX is a Python software package for running complex process
simulations on networkx graphs. A Simulation consists of a network (graph) and a Process that updates the state of the network entities (nodes and edges).

"""

__author__ = "Lukas Ahrenberg <lukas@ahrenberg.se>"

__license__ = "Modified BSD License"

import sys
import os
# A bug workaround I've seen in both networkx and numpy setup.py.
# Only needed for older python versions?
if os.path.exists('MANIFEST'): 
    os.remove('MANIFEST')

from distutils.core import setup 
from glob import glob

import subprocess

sys.path.insert(0, '.')
    
# Names of package and distribution. They differ as the main package is the 
# python code, but the distribution is more.

packagename = 'nepidemix'

distname = 'NepidemiX'

# Basic version
version = '0.2'

is_released = False

# The packages we provide.
packages=['nepidemix', 
          'nepidemix.utilities',
          'nepidemix.utilities.networkxtra',
          'nepidemix.utilities.networkxtra.generators']



# Requirements
required_packages = ['networkx (>= 1.4)']

# Program scripts
scripts = ['scripts/nepidemix_runsimulation', 'scripts/nepidemix_initclustersim']


def globitall(dir, globtype = '*'):
    """
    Recursively go though dir and all its sub directories constructing a
    list of data_data files compatible pairs with all paths rooted in dir.
    
    """
    mylist = []
    totallist = []
    thefiles = glob(os.path.join(dir,globtype))
    for afile in thefiles:
        if not os.path.isdir(afile):
            mylist.append(afile)
    if len(mylist) > 0:
        totallist.append(('', mylist))
    
    allindir = glob(os.path.join(dir,'*'))
    for adir in allindir:
        if os.path.isdir(adir):
            childhead = os.path.split(adir)[1]
            childlist = globitall(adir, globtype)
            for chdir, chlist in childlist:
                totallist.append((os.path.join(childhead,chdir),chlist))

    return totallist


# Data such as documentation.
data = []
# Put documentation under a share/doc/distname-version directory in the 
# install path.
docdirbase  = os.path.join('share','doc',"{0}-{1}".format(distname, version))

# Add README.txt, INSTALL.txt, and LICENSE.txt et c.
data.append((docdirbase, glob('*.txt')))
# Add all documentation under the sphinx html build directory.
allhtml = globitall(os.path.join('doc','_build', 'html'))
for subpath, filelist in allhtml:
    data.append((os.path.join(docdirbase,'html', subpath), filelist))

# Add the tutorial_examples directory.
allexamples = globitall(os.path.join('doc','examples'))
for subpath, filelist in allexamples:
    data.append((os.path.join(docdirbase,'examples', subpath), filelist))


# git_version adapted from numpy setup.py (BSD licence)
# Copyright (c) 2005-2009, NumPy Developers.
# All rights reserved.
# Return the git revision as a string
def git_version():
    def _minimal_ext_cmd(cmd):
        # construct minimal environment
        env = {}
        for k in ['SYSTEMROOT', 'PATH']:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        # LANGUAGE is used on win32
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(cmd, stdout = subprocess.PIPE, env=env).communicate()[0]
        return out

    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        GIT_REVISION = out.strip().decode('ascii')
    except OSError:
        GIT_REVISION = "Unknown"

    return GIT_REVISION

# write_version adapted from numpy setup.py (BSD licence)
# Copyright (c) 2005-2009, NumPy Developers.
# All rights reserved.
# Modification to work on local variables and use param string.
# Return the git revision as a string
def write_version_py(version, is_released, filename='nepidemix/version.py'):
    cnt = """
# THIS FILE IS GENERATED FROM NepidemiX setup.py
short_version = '%(version)s'
version = '%(version)s'
full_version = '%(full_version)s'
git_revision = '%(git_revision)s'
release = %(isrelease)s

if not release:
    version = full_version
"""
    # Adding the git rev number needs to be done inside write_version_py(),
    # otherwise the import of version messes up the build under Python 3.
    full_version = version
    if os.path.exists('.git'):
        git_revision = git_version()
    elif os.path.exists('nepidemix/version.py'):
        # must be a source distribution, use existing version file
        try:
            sys.path.insert(0, 'nepidemix')
            from version import git_revision
        except ImportError:
            raise ImportError("Unable to import git_revision. Try removing " \
                              "nepidemix/version.py and the build directory " \
                              "before building.")
    else:
        git_revision = "Unknown"

    if not is_released:
        full_version += '.dev-' + git_revision[:7]

    a = open(filename, 'w')
    try:
        a.write(cnt % {'version': version,
                       'full_version' : full_version,
                       'git_revision' : git_revision,
                       'isrelease': str(is_released)})
    finally:
        a.close()


if __name__ == "__main__":

    # Update version file.
    write_version_py(version, is_released)

    from nepidemix.version import version

    doclines = __doc__.split("\n")
    

    # Run setup.
    setup(name=distname,
          version=version,
          packages=packages,
          scripts = scripts,
          data_files = data,
          author = 'Nepidemix Developers',
          author_email = 'lukas@ahrenberg.se',
          maintainer = 'Lukas Ahrenberg',
          maintainer_email = 'lukas@ahrenberg.se',
          requires = required_packages,
          provides = [distname, packagename],
          url = "www.impact-hiv.irmacs.sfu.ca",
          description = doclines[1],
          long_description = "\n".join(doclines[3:]),
          download_url = "",
          license = __license__,
    )


