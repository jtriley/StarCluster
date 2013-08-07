.. _boto-plugin:

###########
Boto Plugin
###########
.. _Boto: https://github.com/boto/boto

This plugin configures a $HOME/.boto config file for the ``CLUSTER_USER``. It
supports both copying an existing boto config file and auto-generating a boto
config file using the currently active StarCluster credentials.

To use this plugin you must first define it in the StarCluster config file:

.. code-block:: ini

    [plugin boto]
    setup_class = starcluster.plugins.boto.BotoPlugin

By default the plugin auto-generates a boto config file for you using the
currently active AWS credentials at the time the plugin is executed. If you'd
prefer to copy your own boto config file instead add the ``boto_cfg`` setting:

.. code-block:: ini

    [plugin boto]
    setup_class = starcluster.plugins.boto.BotoPlugin
    boto_cfg = /path/to/your/boto/config

Once you've defined the plugin in your config, add the boto plugin to the list
of plugins in one of your cluster templates:

.. code-block:: ini

    [cluster smallcluster]
    plugins = boto

Now whenever you start a cluster using that cluster template the
``CLUSTER_USER`` will automatically be configured to use boto.
