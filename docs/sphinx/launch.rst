Launching a StarCluster on Amazon EC2
=====================================

Use the **start** command in StarCluster to launch a new cluster on Amazon EC2. 
The start command takes two arguments: the cluster template and a tagname 
for cluster identification.

Below is an example of starting a StarCluster from the *default* cluster template 
defined in the config and tagged as *physicscluster*. This example will be used throughout
this section.

.. code-block:: none

        $ starcluster start physicscluster # this line starts the cluster
        StarCluster - (http://web.mit.edu/starcluster)
        Software Tools for Academics and Researchers (STAR)
        Please submit bug reports to starcluster@mit.edu

        >>> Using default cluster template: smallcluster
        >>> Validating cluster template settings...
        >>> Cluster template settings are valid
        >>> Starting cluster...
        >>> Launching a 2-node cluster...
        >>> Launching master node...
        >>> Master AMI: ami-17b15e7e
        >>> Creating security group @sc-physicscluster...
        RESERVATION r-d71f20be 123456789012 default
        INSTANCE i-10e91578 ami-17b15e7e pending gsg-keypair 0 m1.small ...
        >>> Launching worker nodes...
        >>> Node AMI: ami-17b15e7e
        RESERVATION r-ab1f20c2 123456789012 default
        INSTANCE i-14e9157c ami-17b15e7e pending gsg-keypair 0 m1.small ...
        >>> Waiting for cluster to start... 
        >>> The master node is ec2-123-12-12-123.compute-1.amazonaws.com
        >>> Attaching volume vol-99999999 to master node on /dev/sdz ...
        >>> Setting up the cluster...
        >>> Mounting EBS volume vol-99999999 on /home...
        >>> Using private key /home/user/.ssh/id_rsa-gsg-keypair (rsa)
        >>> Creating cluster user: myuser
        >>> Using private key /home/user/.ssh/id_rsa-gsg-keypair (rsa)
        >>> Configuring scratch space for user: myuser
        >>> Configuring /etc/hosts on each node
        >>> Configuring NFS...
        >>> Configuring passwordless ssh for root
        >>> Configuring passwordless ssh for user: myuser
        >>> Generating local RSA ssh keys for user: myuser
        >>> Installing Sun Grid Engine...
        >>> Done Configuring Sun Grid Engine
        >>> 

        The cluster has been started and configured. 

        Login to the master node as root by running: 

            $ starcluster sshmaster physicscluster

        or manually as myuser:

            $ ssh -i /home/user/.ssh/id_rsa-gsg-keypair myuser@ec2-123-12-12-123.compute-1.amazonaws.com

        When you are finished using the cluster, run:

            $ starcluster stop physicscluster

        to shutdown the cluster and stop paying for service

                
        >>> start took 6.922 mins


The output of the **start** command should look similar to the above if everything went successfully.

If you wish to use a different template besides the default, *largecluster* for example, the command becomes:

.. code-block:: none

        $ starcluster start -c largecluster physicscluster

This command will do the same thing as above only using the *largecluster* cluster template.

Managing Multiple Clusters
--------------------------

To list all of your StarClusters on Amazon EC2 run the following command:

.. code-block:: none

        $ starcluster listclusters

The output should look something like:

.. code-block:: none

        $ starcluster listclusters
        StarCluster - (http://web.mit.edu/starcluster)
        Software Tools for Academics and Researchers (STAR)
        Please submit bug reports to starcluster@mit.edu

        ---------------------------------------------------
        physicscluster (security group: @sc-physicscluster)
        ---------------------------------------------------
        Launch time: 2010-02-19T20:55:20.000Z
        Zone: us-east-1c
        Keypair: gsg-keypair
        EBS volumes:
            vol-c8888888 on master:/dev/sdj (status: attached)
        Cluster nodes:
             master running i-99999999 ec2-123-123-123-121.compute-1.amazonaws.com
            node001 running i-88888888 ec2-123-123-123-122.compute-1.amazonaws.com

This will list each StarCluster you've started by tag name.

Logging into the master node
----------------------------
To login to the master node as root:

.. code-block:: none 

        $ starcluster sshmaster physicscluster

or as user sgeadmin:

.. code-block:: none 

        $ starcluster sshmaster -u sgeadmin physicscluster

Logging into the worker nodes
-----------------------------
To login to a worker node as root:

.. code-block:: none 

        $ starcluster sshnode physicscluster node001

or as user sgeadmin:

.. code-block:: none 

        $ starcluster sshnode -u sgeadmin physicscluster node001

The above commands will ssh to node001 of the *physicscluster*.

Shutting Down a Cluster
-----------------------
Once you've finished using the cluster and wish to stop paying for it, simply run the **stop** command
providing the cluster tag name you gave when starting:

.. code-block:: none
        
        $ starcluster stop physicscluster

This command will prompt for confirmation before destroying the cluster:

.. code-block:: none

        $ starcluster stop physicscluster
        StarCluster - (http://web.mit.edu/starcluster)
        Software Tools for Academics and Researchers (STAR)
        Please submit bug reports to starcluster@mit.edu

        Shutdown cluster physicscluster (y/n)? y
        >>> Shutting down i-99999999
        >>> Shutting down i-88888888
        >>> Removing cluster security group @sc-physicscluster

This will terminate all instances in the cluster tagged "physicscluster" and removes the @sc-physicscluster
security group.
