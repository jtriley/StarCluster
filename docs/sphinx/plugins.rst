StarCluster Plugin System
=========================
StarCluster has support for user contributed plugins. Plugins allow developers to further configure the cluster on top of
the default cluster configuration provided by StarCluster. Plugins are used to provide custom cluster configurations for a variety
of computing needs.

Creating a New Plugin
---------------------
A StarCluster plugin is simply a Python class that extends **starcluster.clustersetup.ClusterSetup** and implements a *run* method.
This class must live in a module that is on the PYTHONPATH. By default, StarCluster will add the ~/.starcluster/plugins directory
to the PYTHONPATH automatically. The ~/.starcluster/plugins directory is not created automatically so you will need to create it if 
it does not exist.

Below is a very simple example of a StarCluster plugin that installs a package on each node using apt-get after the cluster has been 
configured:

.. code-block:: python

        from starcluster.clustersetup import ClusterSetup

        class PackageInstaller(ClusterSetup):
             def __init__(self, pkg_to_install):
                  self.pkg_to_install = pkg_to_install
             def run(self, nodes, master, user, user_shell, volumes):
                  for node in nodes:
                       node.ssh.execute('apt-get -y install %s' % self.pkg_to_install)

For this example we assume that this class lives in a module file called **ubuntu.py** and that this file lives in the
~/.starcluster/plugins directory.

This is a very simple example that simply demonstrates how to execute a command on each node in the cluster. For a more sophisticated
example, have a look at StarCluster's default setup class **starcluster.clustersetup.DefaultClusterSetup**. This is the class used to perform
StarCluster's default setup routines. The DefaultClusterSetup class should provide you with a more complete example of the plugin API and 
the types of things you can do with the arguments passed to a plugin's *run* method.

Adding Your Plugin to the Config
--------------------------------
To use a plugin we must first add it to the config and then add the plugin's config to a *cluster template*. Below is an example config
for the example plugin above:

.. code-block:: ini

        [plugin pkginstaller]
        setup_class = ubuntu.PackageInstaller
        pkg_to_install = htop

In this example, pkg_to_install is an argument to the plugin's constructor (ie __init__). A plugin can, of course, define multiple
construtor arguments and you can configure these arguments in the config similar to *pkg_to_install* in the above example.

After you've defined a **[plugin]** section, you can now use this plugin in a *cluster template* by configuring its **plugins** setting:

.. code-block:: ini

        [cluster smallcluster]
        ....
        plugins = pkginstaller

This setting instructs StarCluster to run the *pkginstaller* plugin after StarCluster's default setup routines. If you want to use more
than one plugin in a template you can do so by providing a list of plugins:

.. code-block:: ini

        [cluster smallcluster]
        ....
        plugins = pkginstaller, myplugin

In the example above, starcluster would first run the *pkginstaller* plugin and then the *myplugin* plugin afterwards. In short, order matters
when defining plugins to use in a *cluster template*.
