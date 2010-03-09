**********************
Installing StarCluster
**********************
StarCluster is available via the Python Package Index (PyPI) and comes with two public Amazon EC2 AMIs (i386 and x86_64).
Below are instructions for installing the latest stable release of StarCluster via PyPI (**recommended**). There are also
instructions for installing the latest development version from github for advanced users.

Install Latest Stable Release from PyPI
=======================================
To install the latest stable release of StarCluster from the PYthon Package Index (PYPI) on Linux/Mac operating systems, 
execute the following command in a terminal:

.. code-block:: ini

    $ sudo easy_install StarCluster
    (enter your root/admin password)

Assuming this command completes successfully you're now ready to create the configuration file.

Manually Install Latest Stable Release from PyPI
------------------------------------------------
To manually install StarCluster from the PYthon Package Index (PYPI) on Linux/Mac operating systems, download 
StarCluster-XXX.tar.gz from http://pypi.python.org/pypi/StarCluster. Then change to the directory you downloaded
StarCluster-XXX.tar.gz to and execute the following in a terminal:

.. code-block:: ini

    $ tar xvzf StarCluster-XXX.tar.gz
    $ cd StarCluster-XXX
    $ sudo python ez_setup.py install
    $ sudo python setup.py install

Assuming this command completes successfully you're now ready to create the configuration file.

Install development version from github
=======================================

**WARNING**: These methods describe installing the latest development snapshot. Although we try to keep the latest code functional, 
please be aware that things may break with these snapshots and that you use them at your own risk. This section is really only 
meant for those that are interested in contributing to or testing the latest development code.

There are two ways to install the latest development version of StarCluster from github:

Install development version using a downloaded snapshot
-------------------------------------------------------
This method does not require any special tools other than a web browser and python and is recommended if you don't use git but 
would still like the latest development changes.

Download a `zip <http://github.com/jtriley/StarCluster/zipball/master>`_ or `tar <http://github.com/jtriley/StarCluster/zipball/master>`_ 
snapshot of the latest development code.

After downloading the code, perform the following in a terminal to install:

.. code-block:: ini

    $ cd StarCluster
    $ sudo python ez_setup.py install
    $ sudo python setup.py install

Assuming this command completes successfully you're now ready to create the configuration file.

.. code-block:: ini

    $ starcluster help

Install development version using git
-------------------------------------
This method requires that you have git installed on your machine. If you're unsure, either use the latest development snapshot as 
described above, or install the latest stable version from pypi.

.. code-block:: ini

    $ git clone git://github.com/jtriley/StarCluster.git
    $ cd StarCluster
    $ sudo python ez_setup.py install
    $ sudo python setup.py install

After this is complete, you will need to setup the configuration file.

.. code-block:: ini

    $ starcluster help
