.. _pypackage-plugin:

###############################
Python Package Installer Plugin
###############################

The ``PyPackageSetup`` plugin installs a list of Python packages on all nodes
in parallel using `pip <https://pypi.python.org/pypi/pip>`_ (by default).

*****
Usage
*****

To use this plugin add the following to your starcluster config file with the list
of packages to install. For instance to install libraries to build an HTTP API
with a database:

.. code-block:: ini

    [plugin webapp-packages-installer]
    setup_class = starcluster.plugins.pypackage.PyPackageSetup
    packages = flask, SQLAlchemy

The ``packages`` setting specifies the list of Python packages to install on
each node.

Once you've configured the ``PyPackageSetup`` plugin the next step is to add
it to the ``plugins`` list in one of your cluster templates in the config:

.. code-block:: ini

    [cluster mycluster]
    plugins = webapp-packages-installer

If you already have a cluster running that didn't originally include the
``PyPackageSetup`` plugin in it's config you can manually run the plugin on
the cluster using::

    $ starcluster runplugin webapp-packages-installer mycluster
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Running plugin webapp-packages-installer
    >>> Installing Python packages on all nodes:
    >>> $ pip install -U flask
    >>> $ pip install -U SQLAlchemy
    2/2 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%


******************************
Installing unreleased software
******************************

pip can also install the development branch of software project directly from
source code repositories such as github. For insance the following configuration
makes it possible to install the master branch of IPython. If this plugin is
configured to run before :ref:`ipcluster-plugin`, this makes it possible to run the
lastest unreleased feature of IPython.parallel and notebook::

    [plugin ipython-dev]
    setup_class = starcluster.plugins.pypackage.PyPackageSetup
    packages = pyzmq,
               python-msgpack,
               git+http://github.com/ipython/ipython.git

    [plugin ipcluster]
    setup_class = starcluster.plugins.ipcluster.IPCluster
    enable_notebook = True

    [cluster mycluster]
    plugins = ipython-dev, ipcluster