Launching a StarCluster on Amazon EC2
=====================================

Use the **start** command in StarCluster to launch a new cluster on Amazon EC2. 
The start command takes two arguments: the cluster template and a tagname 
for cluster identification.

Below is an example of starting a StarCluster from the *smallcluster* config
template and tagged as *physicscluster*. This example will be used throughout
the page.

.. code-block:: none

        $ starcluster start smallcluster physicscluster # this line starts the cluster

        StarCluster - (http://web.mit.edu/starcluster)
        Author: justin.t.riley@gmail.com
        Please submit bug reports to starcluster@mit.edu

        >>> Starting cluster...
        >>> Launching a 4-node cluster...
        >>> Launching master node...
        >>> MASTER AMI: ami-a19e71c8
        RESERVATION r-d71f20be 123456789012 default
        INSTANCE i-10e91578 ami-a19e71c8 pending gsg-keypair 0 c1.xlarge ...
        >>> Launching worker nodes...
        >>> NODE AMI: ami-a19e71c8
        RESERVATION r-ab1f20c2 123456789012 default
        INSTANCE i-14e9157c ami-a19e71c8 pending gsg-keypair 0 c1.xlarge ...
        INSTANCE i-16e9157e ami-a19e71c8 pending gsg-keypair 1 c1.xlarge ...
        INSTANCE i-e8e91580 ami-a19e71c8 pending gsg-keypair 2 c1.xlarge ...
        >>> Waiting for cluster to start...
        >>> Attaching volume to master node...
        >>> The master node is ec2-174-129-110-23.compute-1.amazonaws.com
        >>> Setting up the cluster...
        >>> Using private key /home/youruser/.ec2/your-id_rsa-gsg-keypair (rsa)
        >>> Using private key /home/youruser/.ec2/your-id_rsa-gsg-keypair (rsa)
        >>> Using private key /home/youruser/.ec2/your-id_rsa-gsg-keypair (rsa)
        >>> Using private key /home/youruser/.ec2/your-id_rsa-gsg-keypair (rsa)
        >>> Mounting EBS volume vol-1234e123 on /home...
        >>> Creating cluster user: sgeadmin
        >>> Configuring scratch space for user: sgeadmin
        >>> Configuring /etc/hosts on each node
        >>> Configuring NFS...
        >>> Configuring passwordless ssh for root
        >>> Configuring passwordless ssh for user: sgeadmin
        >>> Using existing RSA ssh keys found for user: sgeadmin
        >>> Installing Sun Grid Engine...
        >>> Done Configuring Sun Grid Engine
        >>>

        The cluster has been started and configured. ssh into the master node as root by running:

        $ starcluster sshmaster physicscluster

        or as sgeadmin directly:

        $ ssh -i /home/user/.ec2/your-id_rsa-gsg-keypair sgeadmin@ec2-123-123-123-12.compute-1.amazonaws.com

        >>> start_cluster took 4.776 mins

The output of the **start** command should look similar to the above if everything went successfully.

Managing Multiple Clusters
--------------------------

To list all of your StarClusters on Amazon EC2 run the following command:

.. code-block:: none

    $ starcluster listclusters

This will list each StarCluster you've started by tag name (prefixed with **@sc-**)

Logging into the master node
----------------------------
To login to the master node as root:

.. code-block:: none 

        $ starcluster sshmaster physicscluster

Logging into the worker nodes
----------------------------
To login to a worker node as root:

.. code-block:: none 

        $ starcluster sshnode physicscluster 0

The above command will ssh to node001 of the *physicscluster*.
