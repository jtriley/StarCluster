.. _pkginstaller-plugin:

########################
Package Installer Plugin
########################

The ``PackageInstaller`` plugin installs a list of Ubuntu packages on all nodes
in parallel.

*****
Usage
*****
To use this plugin add the following to your starcluster config file:

.. code-block:: ini

    [plugin pkginstaller]
    setup_class = starcluster.plugins.pkginstaller.PackageInstaller
    packages = mongodb, python-pymongo

The ``packages`` setting specifies the list of Ubuntu packages to install on
each node. The above example will install ``mongodb`` and ``python-pymongo`` on
all nodes in the cluster.

Once you've configured the ``PackageInstaller`` plugin the next step is to add
it to the ``plugins`` list in one of your cluster templates in the config:

.. code-block:: ini

    [cluster mycluster]
    plugins = pkginstaller

If you already have a cluster running that didn't originally include the
``PackageInstaller`` plugin in it's config you can manually run the plugin on
the cluster using::

    $ starcluster runplugin pkginstaller mycluster
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Running plugin pkginstaller
    >>> Installing the following packages on all nodes:
    mongodb, python-pymongo
    2/2 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
