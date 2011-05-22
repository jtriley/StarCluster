Contributing to StarCluster
===========================

Sign-up for a Github acount
---------------------------
https://github.com

Fork the StarCluster project
----------------------------
https://github.com/jtriley/StarCluster

Clone your fork
---------------
.. code-block::  ini

    $ git clone <user>@github.com:<user>/StarCluster.git

Using virtualenv
----------------
.. code-block::  ini

    $ pip install virtualenv
    $ pip install virtualenvwrapper

http://pypi.python.org/pypi/virtualenv
http://pypi.python.org/pypi/virtualenvwrapper

Code clean-up
-------------
Before committing any code please be sure to run the check.sh script in the
root of your StarCluster git repo. This script runs pep8 and pyflakes on all
source files and outputs any errors it finds related to pep8 formatting,
syntax, import errors, undefined variables, etc. Please fix any errors reported
before committing. 

.. code-block:: ini

    $ cd $STARCLUSTER_REPO
    $ pip install pep8
    $ pip install pyflakes
    $ ./check.py
    >>> Running pyflakes...
    >>> Running pep8...
    >>> Clean!

Contributing to StarCluster 
TODO
