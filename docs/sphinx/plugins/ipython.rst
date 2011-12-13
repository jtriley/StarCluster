######################
IPython Cluster Plugin
######################
.. _IPython: http://ipython.org
.. note::

    These docs are for `IPython`_ 0.11+ which is installed in the latest
    StarCluster 11.10 Ubuntu-based AMIs. See `starcluster listpublic` for
    a list of available AMIs.

To configure your cluster as an `interactive IPython cluster`_ you must first
define the ``ipcluster`` plugin in your config file:

.. _interactive IPython cluster: http://ipython.org/ipython-doc/stable/parallel/parallel_intro.html#introduction

.. code-block:: ini

    [plugin ipcluster]
    setup_class = starcluster.plugins.ipcluster.IPCluster

After defining the plugin in your config, add the ipcluster plugin to the list
of plugins in one of your cluster templates:

.. code-block:: ini

    [cluster smallcluster]
    plugins = ipcluster

*************************
Using the IPython Cluster
*************************
To use your new IPython cluster log in directly to the master node of the
cluster as the ``CLUSTER_USER`` and create a parallel client::

    $ starcluster sshmaster mycluster -u myuser
    $ ipython
    [~]> from IPython.parallel import Client
    [~]> rc = Client(packer='pickle')

Once the client has been started, create a 'view' over the entire cluster and
begin running parallel tasks. Below is an example of performing a parallel map
across all nodes in the cluster::

    [~]> view = rc[:]
    [~]> results = view.map_async(lambda x: x**30, range(8))
    [~]> print results.get()
    [0,
     1,
     1073741824,
     205891132094649L,
     1152921504606846976L,
     931322574615478515625L,
     221073919720733357899776L,
     22539340290692258087863249L]

.. _IPython parallel docs: http://ipython.org/ipython-doc/stable/parallel
.. seealso::

    See the `IPython parallel docs`_ (0.11+) to learn more about the IPython
    parallel API

***********************************************
Connecting from your Local IPython Installation
***********************************************
.. note::

    You must have IPython 0.11+ installed to use this feature

If you'd rather control the cluster from your local IPython installation use
the ``shell`` command and pass the ``--ipcluster`` option::

    $ starcluster shell --ipcluster=mycluster

This will start StarCluster's development shell and configure a remote parallel
session for you automatically. StarCluster will create a parallel client in a
variable named ``ipclient`` and a corresponding view of the entire cluster in a
variable named ``ipview`` which you can use to run parallel tasks on the remote
cluster::

    $ starcluster shell --ipcluster=mycluster
    [~]> ipclient.ids
    [0, 1, 2, 3]
    [~]> res = ipview.map_async(lambda x: x**30, range(8))
    [~]> print res.get()

***********************************************
Using IPython Parallel Scripts with StarCluster
***********************************************
If you wish to run parallel IPython scripts from your local machine that run on
the remote cluster you will need to use the following configuration when
creating the parallel client in your code::

    from IPython.parallel import Client
    rc = Client('~/.starcluster/ipcluster/<cluster>-<region>.json'
                sshkey='/path/to/cluster/keypair.rsa'
                packer='pickle')

For example, let's say we started a cluster called 'mycluster' in region
'us-east-1' with keypair 'mykey' stored in /home/user/.ssh/mykey.rsa. In this
case the above config should be updated to::

    from IPython.parallel import Client
    rc = Client('/home/user/.starcluster/ipcluster/mycluster-us-east-1.json'
                sshkey='/home/user/.ssh/mykey.rsa'
                packer='pickle')
