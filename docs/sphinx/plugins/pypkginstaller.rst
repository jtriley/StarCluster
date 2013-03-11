.. _pypkginstaller-plugin:

###############################
Python Package Installer Plugin
###############################

The ``PyPkgInstaller`` plugin installs a list of Python packages on all nodes
in parallel using `pip <https://pypi.python.org/pypi/pip>`_ (by default).

*****
Usage
*****

To use this plugin add the following to your starcluster config file with the list
of packages to install. For instance to install libraries to build an HTTP API
with a database:

.. code-block:: ini

    [plugin webapp-packages-installer]
    setup_class = starcluster.plugins.pypkginstaller.PyPkgInstaller
    packages = flask, SQLAlchemy

The ``packages`` setting specifies the list of Python packages to install on
each node.

Once you've configured the ``PyPkgInstaller`` plugin the next step is to add
it to the ``plugins`` list in one of your cluster templates in the config:

.. code-block:: ini

    [cluster mycluster]
    plugins = webapp-packages-installer

If you already have a cluster running that didn't originally include the
``PyPkgInstaller`` plugin in its config you can manually run the plugin on
the cluster using::

    $ starcluster runplugin webapp-packages-installer mycluster
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Running plugin webapp-packages-installer
    >>> Installing Python packages on all nodes:
    >>> $ pip install flask
    >>> $ pip install SQLAlchemy
    2/2 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> PyPkgInstaller took 0.317 mins


******************************
Installing Unreleased Software
******************************

pip can also install the development branch of software project directly from
source code repositories such as github. For instance the following configuration
makes it possible to install the master branch of IPython. If this plugin is
configured to run before :ref:`ipcluster-plugin`, this makes it possible to test
yet unreleased features of IPython.parallel and notebook:

.. code-block:: ini

    [plugin ipython-dev]
    setup_class = starcluster.plugins.pypkginstaller.PyPkgInstaller
    packages = pyzmq,
               python-msgpack,
               git+http://github.com/ipython/ipython.git

    [plugin ipcluster]
    setup_class = starcluster.plugins.ipcluster.IPCluster
    enable_notebook = True

    [cluster mycluster]
    plugins = ipython-dev, ipcluster
