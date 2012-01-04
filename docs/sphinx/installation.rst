**********************
Installing StarCluster
**********************
StarCluster is available via the PYthon Package Index (PyPI) and comes with two
public Amazon EC2 AMIs (i386 and x86_64).  Below are instructions for
installing the latest stable release of StarCluster via PyPI (**recommended**).
There are also instructions for installing the latest development version from
github for advanced users.

Install Latest Stable Release from PyPI
=======================================
To install the latest stable release of StarCluster from the PYthon Package
Index (PYPI) on Linux/Mac operating systems, execute the following command in a
terminal:

.. code-block:: ini

    $ sudo easy_install StarCluster
    (enter your root/admin password)

Assuming this command completes successfully you're now ready to create the
configuration file.

Manually Install Latest Stable Release from PyPI
------------------------------------------------
To manually install StarCluster from the PYthon Package Index (PYPI) on
Linux/Mac operating systems, download StarCluster-XXX.tar.gz from
http://pypi.python.org/pypi/StarCluster. Then change to the directory you
downloaded StarCluster-XXX.tar.gz to and execute the following in a terminal:

.. code-block:: ini

    $ tar xvzf StarCluster-XXX.tar.gz
    $ cd StarCluster-XXX
    $ sudo python distribute_setup.py
    $ sudo python setup.py install

Assuming this command completes successfully you're now ready to create the
configuration file.

Install development version from github
=======================================

.. warning::
    These methods describe installing the latest development snapshot. Although
    we try to keep the latest code functional, please be aware that things may
    break with these snapshots and that you use them at your own risk. This
    section is really only meant for those that are interested in contributing
    to or testing the latest development code.

There are two ways to install the latest development version of StarCluster
from github:

Install development version using a downloaded snapshot
-------------------------------------------------------
This method does not require any special tools other than a web browser and
python and is recommended if you don't use git but would still like the latest
development changes.

Download a `zip <https://github.com/jtriley/StarCluster/zipball/master>`_ or
`tar <https://github.com/jtriley/StarCluster/zipball/master>`_ snapshot of the
latest development code.

After downloading the code, perform the following in a terminal to install:

.. code-block:: ini

    $ cd StarCluster
    $ sudo python distribute_setup.py
    $ sudo python setup.py install

Assuming this command completes successfully you're now ready to create the
configuration file.

.. code-block:: ini

    $ starcluster help

Install development version using git
-------------------------------------
This method requires that you have git installed on your machine. If you're
unsure, either use the latest development snapshot as described above, or
install the latest stable version from pypi.

.. code-block:: ini

    $ git clone git://github.com/jtriley/StarCluster.git
    $ cd StarCluster
    $ sudo python distribute_setup.py
    $ sudo python setup.py install

After this is complete, you will need to setup the configuration file.

.. code-block:: ini

    $ starcluster help

.. _windows-install:

Installing on Windows
=====================
Before attempting to install StarCluster you first need to install Python 2.7
for Windows from `python.org <http://www.python.org/download/>`_. You'll want
to download the "Python 2.7.x Windows Installer".

Once you have Python 2.7 installed the next step is to download and install the
Windows installers for the following dependencies:

* `setuptools 0.6rc11 <http://pypi.python.org/packages/2.7/s/setuptools/setuptools-0.6c11.win32-py2.7.exe>`_
* `pycrypto 2.3 <http://www.voidspace.org.uk/downloads/pycrypto-2.3.win32-py2.7.zip>`_

.. note::

   You will need to have your Python installation's ``Script`` directory (e.g.
   ``C:\Python27\Scripts``) added to the end of your ``%PATH%`` variable in
   order to use both the ``easy_install`` and ``starcluster`` commands below

Once you've installed the above dependencies into your Python 2.7 installation you can now run::

    c:\> easy_install StarCluster

Once the install is finished you're now ready to setup the configuration file::

    c:\> starcluster help
