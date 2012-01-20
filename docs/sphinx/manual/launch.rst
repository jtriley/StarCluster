Launching a StarCluster on Amazon EC2
=====================================
Use the **start** command in StarCluster to launch a new cluster on Amazon EC2.
The start command takes two arguments: the cluster template and a tagname for
cluster identification.

Below is an example of starting a StarCluster from the *default* cluster
template defined in the config and tagged as *physicscluster*. This example
will be used throughout this section.

.. code-block:: none

    $ starcluster start physicscluster # this line starts the cluster
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Validating cluster template settings...
    >>> Cluster template settings are valid
    >>> Starting cluster...
    >>> Launching a 2-node cluster...
    >>> Launching master node (ami: ami-8cf913e5, type: m1.small)...
    >>> Creating security group @sc-physicscluster...
    >>> Waiting for cluster to come up... (updating every 30s)
    >>> Waiting for all nodes to be in a 'running' state...
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Waiting for SSH to come up on all nodes...
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> The master node is ec2-123-12-12-123.compute-1.amazonaws.com
    >>> Setting up the cluster...
    >>> Attaching volume vol-99999999 to master node on /dev/sdz ...
    >>> Configuring hostnames...
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Mounting EBS volume vol-99999999 on /home...
    >>> Creating cluster user: myuser (uid: 1001, gid: 1001)
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring scratch space for user: myuser
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring /etc/hosts on each node
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Configuring NFS...
    >>> Setting up NFS took 0.209 mins
    >>> Configuring passwordless ssh for root
    >>> Configuring passwordless ssh for myuser
    >>> Installing Sun Grid Engine...
    >>> Creating SGE parallel environment 'orte'
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Adding parallel environment 'orte' to queue 'all.q'
    >>> Shutting down threads...
    20/20 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Starting cluster took 6.922 mins

    The cluster is now ready to use. To login to the master node
    as root, run:

        $ starcluster sshmaster physicscluster

    When you are finished using the cluster and wish to
    terminate it and stop paying for service:

        $ starcluster terminate physicscluster

    NOTE: Terminating an EBS cluster will destroy all EBS
    volumes backing the nodes.

    Alternatively, if the cluster uses EBS instances, you can
    use the 'stop' command to put all nodes into a 'stopped'
    state:

        $ starcluster stop physicscluster

    NOTE: Any data stored in ephemeral storage (usually /mnt)
    will be lost!

    This will shutdown all nodes in the cluster and put them in
    a 'stopped' state that preserves the EBS volumes backing the
    nodes. A 'stopped' cluster may then be restarted at a later
    time, without losing data on the local disks, by passing the
    -x option to the 'start' command:

        $ starcluster start -x physicscluster

    This will start all 'stopped' EBS instances and reconfigure
    the cluster.

The output of the **start** command should look similar to the above if
everything went successfully.

If you wish to use a different template besides the default, *largecluster* for
example, the command becomes::

    $ starcluster start -c largecluster physicscluster

This command will do the same thing as above only using the *largecluster*
cluster template.

Managing Multiple Clusters
--------------------------
To list all of your StarClusters on Amazon EC2 run the following command::

    $ starcluster listclusters

The output should look something like::

    $ starcluster listclusters
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    ---------------------------------------------------
    physicscluster (security group: @sc-physicscluster)
    ---------------------------------------------------
    Launch time: 2010-02-19T20:55:20.000Z
    Uptime: 00:29:42
    Zone: us-east-1c
    Keypair: gsg-keypair
    EBS volumes:
        vol-c8888888 on master:/dev/sdj (status: attached)
    Cluster nodes:
         master running i-99999999 ec2-123-123-123-121.compute-1.amazonaws.com
        node001 running i-88888888 ec2-123-123-123-122.compute-1.amazonaws.com
    Total nodes: 2

This will list each StarCluster you've started by tag name.

Logging into the master node
----------------------------
To login to the master node as root::

    $ starcluster sshmaster physicscluster

You can also login as a different user using the ``--user`` (``-u``) option.
For example, to login as the ``sgeadmin`` user::

    $ starcluster sshmaster -u sgeadmin physicscluster

Logging into the worker nodes
-----------------------------
To login to a worker node, say ``node001`` for example, as root::

    $ starcluster sshnode physicscluster node001

You can also login as a different user using the ``--user`` (``-u``) option.
For example, to login as the ``sgeadmin`` user::

    $ starcluster sshnode -u sgeadmin physicscluster node001

Rebooting a Cluster
-------------------
Some times you might encounter an error while starting and setting up a new
cluster or using an existing cluster. Rather than terminating the cluster and
starting a new one to get around the errors, you can instead completely
reconfigure the cluster without terminating instances and wasting
instance-hours using the *restart* command::

    $ starcluster restart physicscluster

This will reboot all of the instances, wait for them to come back up, and then
completely reconfigure the cluster from scratch as if you had terminated and
re-created the cluster.

Terminating a Cluster
---------------------

.. warning::

    Once a cluster has been terminated, any data that was not saved either to
    S3 or an external EBS volume will be lost. Make sure you save any data you
    care to keep to S3 or to an external EBS volume.

Once you've finished using the cluster and wish to stop paying for it, simply
run the **terminate** command providing the cluster tag name you gave when
starting::

    $ starcluster terminate physicscluster

This command will prompt for confirmation before destroying the cluster::

    $ starcluster terminate physicscluster
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    Terminate cluster physicscluster (y/n)? y
    >>> Shutting down i-99999999
    >>> Shutting down i-88888888
    >>> Waiting for cluster to terminate...
    >>> Removing cluster security group @sc-physicscluster

This will terminate all instances in the cluster tagged "physicscluster" and
removes the @sc-physicscluster security group.

Stopping an EBS-backed Cluster
------------------------------
.. note::

    You can not ``stop`` S3-backed clusters - they can only be terminated.

If you used EBS-backed AMIs when creating a cluster, the cluster can optionally
be ``stopped`` instead of terminated::

    $ starcluster stop myebscluster

This will shutdown the entire cluster by putting all instances in a ``stopped``
state rather than terminating them. This allows you to preserve the local root
volumes backing the nodes which would normally be destroyed if you used the
**terminate** command. The cluster will continue to show up in the output of
the **listclusters** command after being stopped, however, you will not be
charged for ``stopped`` instance hours, only for the EBS volume storage backing
the nodes::

    $ starcluster listclusters
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    -------------------------------------------------
    myebscluster (security group: @sc-physicscluster)
    -------------------------------------------------
    Launch time: 2011-10-22T20:55:20.000Z
    Uptime: 00:29:42
    Zone: us-east-1c
    Keypair: gsg-keypair
    Cluster nodes:
         master stopped i-99999999
        node001 stopped i-88888888
    Total nodes: 2

A stopped EBS-backed cluster can be ``started`` later on using::

    $ starcluster start -x myebscluster

This will ``start`` all ``stopped`` nodes in the cluster and reconfigure the
cluster. Once the cluster comes up all data previously stored on the root
volumes backing the nodes before shutdown will be available.

To *completely* destroy an EBS-backed cluster use the **terminate** command::

    $ starcluster terminate myebscluster

This will completely destroy the cluster nodes including the root volumes
backing the nodes. As always, before terminating the cluster you should move
any data you wish to keep either to an external EBS volume or to S3.
