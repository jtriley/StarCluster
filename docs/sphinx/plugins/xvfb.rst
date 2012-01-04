.. _xvfb-plugin:

###########
Xvfb Plugin
###########

Xvfb, or X virtual framebuffer, is an X11 server that performs all graphical
operations in memory without showing any screen output. This plugin configures an
Xvfb server on all nodes in the cluster and sets the ``DISPLAY`` variable on the
nodes accordingly.

*****
Usage
*****
To use this plugin add a plugin section to your starcluster config file:

.. code-block:: ini

    [plugin xvfb]
    setup_class = starcluster.plugins.xvfb.XvfbSetup

Next update the ``PLUGINS`` setting of one or more of your cluster templates to
include the xvfb plugin:

.. code-block:: ini

    [cluster mycluster]
    plugins = xvfb

The next time you start a cluster the Xvfb plugin will automatically be
executed and your ``DISPLAY`` setting will be set to ``:1`` on all nodes. If
you already have a cluster running that didn't originally have Xvfb in its
plugin list you can manually run the plugin using::

    $ starcluster runplugin xvfb mycluster
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Running plugin xvfb
    >>> Installing Xvfb on all nodes
    3/3 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Launching Xvfb Server on all nodes
    3/3 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%

Now anytime you login and launch a graphical application on the nodes the
application will be started and rendered within the virtual framebuffer on
``DISPLAY=:1``
