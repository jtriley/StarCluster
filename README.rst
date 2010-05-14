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
* Boto 1.9b+
* Paramiko 1.7.6+

Getting Started:
----------------

To install StarCluster using easy_install::

    $ sudo easy_install StarCluster

To install StarCluster manually::

    $ (Download StarCluster from http://web.mit.edu/starcluster)
    $ tar xvzf starcluster-X.X.X.tar.gz  (where x.x.x is a version number)
    $ cd starcluster-X.X.X
    $ sudo python setup.py install

To run StarCluster::

    $ starcluster help
    
This will give you a template to create a configuration file with your EC2 info, preferences, etc.  
The next step is to customize this file using your favorite text-editor:::

    $ vi ~/.starclustercfg  

Next we start a cluster tagged "mycluster" using the default cluster template in the config.
The default_template setting in the [global] section of the config specifies the default cluster template.::

    $ starcluster start mycluster 

After the above command completes you should now have a working cluster. Once you've finished using the 
cluster and wish to stop paying for it:::

    $ starcluster stop mycluster 

Have a look at the rest of StarCluster's commands::

    $ starcluster help

Licensing:
----------
| StarCluster is licensed under the LGPL
| see COPYING.LESSER (LGPL) and COPYING (GPL) for LICENSE details
