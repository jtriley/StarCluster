.. _plugin_system:

StarCluster Plugin System
=========================
StarCluster has support for user contributed plugins. Plugins allow developers
to further configure the cluster in addition to the default cluster
configuration provided by StarCluster. Plugins are used to provide custom
cluster configurations for a variety of computing needs.

Creating a New Plugin
---------------------
A StarCluster plugin is simply a Python class that extends
**starcluster.clustersetup.ClusterSetup** and implements a *run* method.  This
class must live in a module that is on the PYTHONPATH. By default, StarCluster
will add the ~/.starcluster/plugins directory to the PYTHONPATH automatically.
The ~/.starcluster/plugins directory is not created automatically so you will
need to create it if it does not exist.

Below is a very simple example of a StarCluster plugin that installs a package
on each node using apt-get after the cluster has been configured:

.. code-block:: python

    from starcluster.clustersetup import ClusterSetup

    class PackageInstaller(ClusterSetup):
         def __init__(self, pkg_to_install):
              self.pkg_to_install = pkg_to_install
         def run(self, nodes, master, user, user_shell, volumes):
              for node in nodes:
                   node.ssh.execute('apt-get -y install %s' % self.pkg_to_install)

For this example we assume that this class lives in a module file called
**ubuntu.py** and that this file lives in the ~/.starcluster/plugins directory.

This is a very simple example that simply demonstrates how to execute a command
on each node in the cluster. For a more sophisticated example, have a look at
StarCluster's default setup class
**starcluster.clustersetup.DefaultClusterSetup**. This is the class used to
perform StarCluster's default setup routines. The DefaultClusterSetup class
should provide you with a more complete example of the plugin API and the types
of things you can do with the arguments passed to a plugin's *run* method.

Using the Logging System
------------------------
When writing plugins it's better to use StarCluster's logging system rather
than print statements in your code. This is because the logging system handles
formatting messages and writing them to the StarCluster debug file. Here's a
modified version of the *PackageInstaller* plugin above that uses the logging
system:

.. code-block:: python

    from starcluster.clustersetup import ClusterSetup
    from starcluster.logger import log

    class PackageInstaller(ClusterSetup):
         def __init__(self, pkg_to_install):
              self.pkg_to_install = pkg_to_install
              log.debug('pkg_to_install = %s' % pkg_to_install)
         def run(self, nodes, master, user, user_shell, volumes):
              for node in nodes:
                   log.info("Installing %s on %s" % (self.pkg_to_install, node.alias))
                   node.ssh.execute('apt-get -y install %s' % self.pkg_to_install)

The first thing you'll notice is that we've added an additional import
statement to the code. This line imports the log object that you'll use to log
messages. In the plugin's constructor we've added a log.debug() call that shows
the current value of the pkg_to_install variable.  All messages logged with the
log.debug() method will always be printed to the debug file, however, these
messages will only be printed to the screen if the user passes the --debug flag
to the starcluster command.

In the plugin's *run* method, we've added a log.info() call to notify the user
that the package they specified in the config is being installed on a
particular node. All messages logged with the log.info() method will always be
printed to the screen and also go into the debug file. In addition to
log.info() and log.debug() there are also log.warn(), log.critical(),
log.fatal(), and log.error() methods for logging messages of varying severity.

Adding Your Plugin to the Config
--------------------------------
To use a plugin we must first add it to the config and then add the plugin's
config to a *cluster template*. Below is an example config for the example
plugin above:

.. code-block:: ini

    [plugin pkginstaller]
    setup_class = ubuntu.PackageInstaller
    pkg_to_install = htop

In this example, pkg_to_install is an argument to the plugin's constructor (ie
__init__). A plugin can, of course, define multiple constructor arguments and
you can configure these arguments in the config similar to *pkg_to_install* in
the above example.

After you've defined a **[plugin]** section, you can now use this plugin in a
*cluster template* by configuring its **plugins** setting:

.. code-block:: ini

    [cluster smallcluster]
    ....
    plugins = pkginstaller

This setting instructs StarCluster to run the *pkginstaller* plugin after
StarCluster's default setup routines. If you want to use more than one plugin
in a template you can do so by providing a list of plugins:

.. code-block:: ini

    [cluster smallcluster]
    ....
    plugins = pkginstaller, myplugin

In the example above, starcluster would first run the *pkginstaller* plugin and
then the *myplugin* plugin afterwards. In short, order matters when defining
plugins to use in a *cluster template*.

Using the Development Shell
---------------------------
To launch StarCluster's development shell, use the *shell* command::

    $ starcluster shell
    StarCluster - (http://web.mit.edu/starcluster) (v. 0.9999)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Importing module config
    >>> Importing module plugins
    >>> Importing module cli
    >>> Importing module awsutils
    >>> Importing module ssh
    >>> Importing module utils
    >>> Importing module static
    >>> Importing module exception
    >>> Importing module cluster
    >>> Importing module node
    >>> Importing module clustersetup
    >>> Importing module image
    >>> Importing module volume
    >>> Importing module tests
    >>> Importing module templates
    >>> Importing module optcomplete
    >>> Importing module boto
    >>> Importing module paramiko

    [~]|1>

.. _IPython: http://ipython.scipy.org

This launches you into an IPython_ shell with all of the StarCluster modules
automatically loaded. You'll also notice that you have the following variables
available to you automagically:

1. **cm** - manager object for clusters (``starcluster.cluster.ClusterManager``)
2. **cfg** - object for retrieving values from the config file
   (``starcluster.config.StarClusterConfig``)
3. **ec2** - object for interacting with EC2 (``starcluster.awsutils.EasyEC2``)
4. **s3** - object for interacting with S3 (``starcluster.awsutils.EasyS3``)

Plugin Development Workflow
---------------------------
The process of developing and testing a plugin generally goes something like
this:

1. Start a small test cluster (2-3 nodes)::

    $ starcluster start testcluster -s 2

2. Install and configure the additional software/settings by hand and note the
   steps involved::

    $ starcluster sshmaster testcluster
    root@master $ apt-get install myapp
    ...

3. Write a first draft of your plugin that attempts to do these steps
   programmatically

4. Add your plugin to the StarCluster configuration file

5. Test your plugin on your small test cluster using the **runplugin** command::

    $ starcluster runplugin myplugin testcluster

   Alternatively, you can also run your plugin using the development shell
   (requires IPython_)::

    $ starcluster shell
    [~]> cm.run_plugin('myplugin', 'testcluster')

6. Fix any coding errors in order to get the plugin to run from start to finish
   using the **runplugin** command.

7. Login to the master node and verify that the plugin was successful::

    $ starcluster sshmaster testcluster
