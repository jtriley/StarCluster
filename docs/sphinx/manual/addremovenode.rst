#########################
Adding and Removing Nodes
#########################
StarCluster has support for manually shrinking and expanding the size of your
cluster based on your resource needs. For example, you might start out with
10-nodes and realize that you only really need 5 or the reverse case where you
start 5 nodes and find out you need 10. In these cases you can use
StarCluster's ``addnode`` and ``removenode`` commands to scale the size of your
cluster to your needs.

.. note::
    The examples below assume we have a 1-node cluster running called
    *mycluster*.

************
Adding Nodes
************
To add nodes to a running cluster use the ``addnode`` command. This command takes
a *cluster tag* as an argument and will automatically add a new node to the
cluster::

    $ starcluster addnode mycluster
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Launching node(s): node001
    >>> Waiting for node(s) to come up... (updating every 30s)
    >>> Waiting for open spot requests to become active...
    2/2 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Waiting for all nodes to be in a 'running' state...
    2/2 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Waiting for SSH to come up on all nodes...
    2/2 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring hostnames...
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring /etc/hosts on each node
    2/2 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring NFS...
    >>> Mounting shares for node node001
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring scratch space for user: myuser
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring passwordless ssh for root
    >>> Using existing key: /root/.ssh/id_rsa
    >>> Configuring passwordless ssh for myuser
    >>> Using existing key: /home/myuser/.ssh/id_rsa
    >>> Adding node001 to SGE

The ``addnode`` command auto-generates an alias for the new node(s). In the
above example `mycluster` is a single node cluster. In this case ``addnode``
automatically added a new node and gave it an alias of *node001*. If we added
additional nodes they would be named *node002*, *node003*, and so on.

If you'd rather manually specify an alias for the new node(s) use the ``--alias
(-a)`` option::

    $ starcluster addnode -a mynewnode mycluster

It is also possible to add multiple nodes using the ``--num-nodes (-n)``
option::

    $ starcluster addnode -n 5 mycluster

The above command will add five additional nodes to `mycluster` auto-generating
the node aliases. To specify aliases for all five nodes simply specify a comma
separated list to the ``-a`` option::

    $ starcluster addnode -n 5 -a n1,n2,n3,n4,n5 mycluster

Once the ``addnode`` command has completed successfully the new nodes will show
up in the output of the ``listclusters`` command::

    $ starcluster listclusters mycluster

You can login directly to a new node by alias::

    $ starcluster sshnode mycluster mynewnode

The ``addnode`` command has additional options for customizing the new node's
instance type, AMI, spot bid, and more. See the help menu for a detailed list
of all available options::

    $ starcluster addnode --help

Re-adding a Node
================
If you've previously attempted to add a node and it failed due to a plugin
error or other bug or if you used the ``removenode`` command with the ``-k``
option and wish to re-add the node to the cluster without launching a new
instance you can use the ``-x`` option::

    $ starcluster addnode -x -a node001 mycluster

.. note:: The ``-x`` option requires the ``-a`` option

This will attempt to add or re-add `node001` to mycluster using the existing
instance rather than launching a new instance. If no instance exists with the
alias specified by the ``-a`` option an error is reported. You can also do this
for multiple nodes::

    $ starcluster addnode -x -a mynode1,mynode2,mynode3 mycluster

**************
Removing Nodes
**************
To remove nodes from an existing cluster use the ``removenode`` command. This
command takes at least two arguments: the *cluster tag* representing the
cluster you want to remove nodes from and a node *alias*::

    $ starcluster removenode mycluster node001
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Removing node node001 (i-8bec7ce5)...
    >>> Removing node001 from SGE
    >>> Removing node001 from known_hosts files
    >>> Removing node001 from /etc/hosts
    >>> Removing node001 from NFS
    >>> Canceling spot request sir-3567ba14
    >>> Terminating node: node001 (i-8bec7ce5)

The above command removes `node001` from `mycluster` by removing the node from
the Sun Grid Engine queuing system, from each node's ssh known_hosts files,
from each node's /etc/hosts file, and from all NFS shares. If you're using
plugins with your cluster they will be called to remove the node. Once the node
has been removed from the cluster the node is terminated. If the node is a spot
instance, as it is in the above example, the spot instance request will also be
cancelled.

You can also remove multiple nodes by providing a list of aliases::

    $ starcluster removenode mycluster node001 node002 node003

Remove Without Terminating
==========================
If you'd rather not terminate the node(s) after removing from the cluster to
test plugins, for example, use the ``--keep-instance (-k)`` option::

    $ starcluster removenode -k mycluster node001 node002 node003

This will remove the nodes from the cluster but leave the instances
running. This can be useful, for example, when testing on_add_node methods
in a StarCluster plugin.
