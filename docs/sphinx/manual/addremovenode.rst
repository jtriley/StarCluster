Adding and Removing Nodes from StarCluster
==========================================
StarCluster has support for manually shrinking and expanding the size of your
cluster based on your resource needs. For example, you might start out with
10-nodes and realize that you only really need 5 or the reverse case where you
start 5 nodes and find out you need 10. In these cases you can use
StarCluster's *addnode* and *removenode* commands to scale the size of your
cluster to your needs.

.. note::
    The examples below assume we have a 1-node cluster running called
    *mycluster*.

Adding Nodes
------------
Adding nodes is done using the *addnode* command. This command takes a *cluster
tag* as an argument and will automatically add a new node to the cluster:

.. code-block:: none

    $ starcluster addnode mycluster
    StarCluster - (http://web.mit.edu/starcluster) (v. 0.9999)
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
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring scratch space for user: myuser
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring passwordless ssh for root
    >>> Using existing key: /root/.ssh/id_rsa
    >>> Configuring passwordless ssh for myuser
    >>> Using existing key: /home/myuser/.ssh/id_rsa
    >>> Adding node001 to SGE

If the --alias option is not specified StarCluster will apply the next
available *nodeXXX* alias based on the current size of the cluster. In the
above example only a *master* node existed so StarCluster automatically added
the second node as *node001*. Similarly we had a *master* and *node001* then
running addnode would name the new node *node002*.

You can also manually specify an alias for the new node using the --alias (-a)
option::

    $ starcluster addnode -a mynewnode mycluster

Running listclusters will then show your alias for the node in its output::

    $ starcluster listclusters mycluster

And you can login directly to the new node by alias::

    $ starcluster sshnode mycluster mynewnode

Removing Nodes
--------------
StarCluster also has the ability to remove an existing cluster node's via the
*removenode* command. This command takes at least two arguments: the *cluster
tag* representing the cluster you want to remove nodes from and a node *alias*::

    % starcluster removenode mycluster node001
    StarCluster - (http://web.mit.edu/starcluster) (v. 0.9999)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Removing node node001 (i-8bec7ce5)...
    >>> Removing node001 from SGE
    >>> Removing node001 from known_hosts files
    >>> Removing node001 from /etc/hosts
    >>> Removing node001 from NFS
    >>> Canceling spot request sir-3567ba14
    >>> Terminating node: node001 (i-8bec7ce5)

The above command takes care to properly remove the node from the cluster by
removing the node from the Sun Grid Engine queuing system, each node's ssh
known_hosts file, /etc/hosts file, and from all NFS shares. Afterwards the node
is terminated. If the node is a spot instance, as it is in the above example,
the spot instance request will also be cancelled.
