IPython Cluster Plugin
======================
To configure your cluster as an interactive IPython cluster use the ipcluster plugin:

.. code-block:: ini

        [plugin ipcluster]
        setup_class = starcluster.plugins.ipcluster.IPCluster

The next step is to put the ipcluster plugin in the list of plugins in one of your cluster templates:

.. code-block:: ini

        [cluster smallcluster]
        ...
        plugins = ipcluster
        ...
