StarCluster
===========
| Homepage: http://web.mit.edu/starcluster
| Author: Justin Riley (justin.t.riley@gmail.com)
| Team: Software Tools for Academics and Researchers (http://web.mit.edu/star)

Description:
------------
StarCluster is a utility for creating and managing computing clusters hosted on 
Amazon's Elastic Compute Cloud (EC2). StarCluster utilizes Amazon's EC2 web service 
to create and destroy clusters of Linux virtual machines on demand.

To get started, the user creates a simple configuration file with their AWS account 
details and a few cluster preferences (e.g. number of machines, machine type, ssh 
keypairs, etc). After creating the configuration file and running StarCluster's 
"start" command, a cluster of Linux machines configured with the Sun Grid Engine 
queuing system, an NFS-shared /home directory, and OpenMPI with password-less ssh is 
created and ready to go out-of-the-box. Running StarCluster's "stop" command will 
shutdown the cluster and stop paying for service. This allows the user to only pay 
for what they use.

StarCluster can also utilize Amazon's Elastic Block Storage (EBS) volumes to provide 
persistent data storage for a cluster. EBS volumes allow you to store large amounts 
of data in the Amazon cloud and are also easy to back-up and replicate in the cloud. 
StarCluster will mount and NFS-share any volumes specified in the config. StarCluster's 
"createvolume" command provides the ability to automatically create, format, and 
partition new EBS volumes for use with StarCluster.

StarCluster provides a Ubuntu-based Amazon Machine Image (AMI) in 32bit and 64bit 
architectures. The AMI contains an optimized NumPy/SciPy/Atlas/Blas/Lapack 
installation compiled for the larger Amazon EC2 instance types. The AMI also comes
with Sun Grid Engine (SGE) and OpenMPI compiled with SGE support. The public AMI 
can easily be customized by launching a single instance of the public AMI,
installing additional software on the instance, and then using StarCluster's 
"createimage" command to completely automate the process of creating a new AMI from 
an EC2 instance.

Dependencies:
-------------
* Amazon AWS Account
* Python 2.4+
* Boto 2.0b3
* Paramiko 1.7.6

Getting Started:
----------------

To install StarCluster using easy_install::

    $ sudo easy_install StarCluster

To install StarCluster manually::

    $ (Download StarCluster from http://web.mit.edu/starcluster)
    $ tar xvzf starcluster-X.X.X.tar.gz  (where x.x.x is a version number)
    $ cd starcluster-X.X.X
    $ sudo python setup.py install

After the software has been installed, the next step is to setup the configuration file: ::

    $ starcluster help
    
This will give you a template to use to create a configuration file containing your AWS credentials, 
cluster settings, etc.  The next step is to customize this file using your favorite text-editor: ::

    $ vi ~/.starcluster/config  

This file is commented with example "cluster templates". A cluster template defines a set of configuration
settings used to start a cluster. The example config provides a 'smallcluster' template that is
ready to go out-of-the-box. Simply fill in your AWS credentials and keypair info and you're ready to go.

Next we start a cluster named "mycluster" using the default cluster template 'smallcluster' in the example config: ::

    $ starcluster start mycluster 

The *default_template* setting in the [global] section of the config specifies the default cluster template and
is automatically set to 'smallcluster' in the example config.

After the *start* command completes you should now have a working cluster. You can login to the master node as 
root by running: ::

    $ starcluster sshmaster mycluster

Once you've finished using the cluster and wish to stop paying for it: ::

    $ starcluster stop mycluster 

Have a look at the rest of StarCluster's commands: ::

    $ starcluster --help

Learn more...
-------------
Watch an ~8min screencast @ http://web.mit.edu/stardev/cluster

To learn more have a look at the rest of the documentation:
http://web.mit.edu/stardev/cluster/docs

The docs explain the configuration file in detail, how to create/use EBS volumes with StarCluster, and
how to use the Sun Grid Engine queueing system to submit jobs on the cluster.


Licensing:
----------
| StarCluster is licensed under the LGPL
| see COPYING.LESSER (LGPL) and COPYING (GPL) for LICENSE details
