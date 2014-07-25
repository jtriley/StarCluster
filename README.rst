===================
StarCluster v0.95.5
===================
vanilla_improvements notes are at the bottom.

:StarCluster: Cluster Computing Toolkit for the Cloud
:Version: 0.95.5
:Author: Justin Riley <justin.t.riley@gmail.com>
:Team: Software Tools for Academics and Researchers (http://star.mit.edu)
:Homepage: http://star.mit.edu/cluster
:License: LGPL

Description:
============
StarCluster is a utility for creating and managing computing clusters hosted on
Amazon's Elastic Compute Cloud (EC2). StarCluster utilizes Amazon's EC2 web
service to create and destroy clusters of Linux virtual machines on demand.

All that's needed to create your own cluster(s) on Amazon EC2 is an AWS account
and StarCluster. StarCluster features:

* **Simple configuration** - with examples ready to go out-of-the-box
* **Create/Manage Clusters** - simple **start** command to automatically launch
  and configure one or more clusters on EC2
* **Automated Cluster Setup** - includes NFS-sharing, Open Grid Scheduler
  queuing system, Condor, password-less ssh between machines, and more
* **Scientific Computing AMI** - comes with Ubuntu 11.10-based EBS-backed AMI
  that contains Hadoop, OpenMPI, ATLAS, LAPACK, NumPy, SciPy, IPython, and
  other useful libraries
* **EBS Volume Sharing** - easily NFS-share Amazon Elastic Block Storage (EBS)
  volumes across a cluster for persistent storage
* **EBS-Backed Clusters** - start and stop EBS-backed clusters on EC2
* **Cluster Compute Instances** - support for "cluster compute" instance types
* **Expand/Shrink Clusters** - scale a cluster by adding or removing nodes
* **Elastic Load Balancing** - automatically shrink or expand a cluster based
  on Open Grid Scheduler queue statistics
* **Plugin Support** - allows users to run additional setup routines on the
  cluster after StarCluster's defaults. Comes with plugins for IPython
  parallel+notebook, Condor, Hadoop, MPICH2, MySQL cluster, installing Ubuntu
  packages, and more.

Interested? See the `getting started`_ section for more details.

.. _getting started:

Getting Started:
================
Install StarCluster using `easy_install`::

    $ easy_install StarCluster

or using `pip`::

    $ pip install StarCluster

or manually::

    $ (Download StarCluster from http://star.mit.edu/cluster/downloads.html)
    $ tar xvzf starcluster-X.X.X.tar.gz  (where x.x.x is a version number)
    $ cd starcluster-X.X.X
    $ sudo python setup.py install

After the software has been installed, the next step is to setup the
configuration file::

    $ starcluster help
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    !!! ERROR - config file /home/user/.starcluster/config does not exist

    Options:
    --------
    [1] Show the StarCluster config template
    [2] Write config template to /home/user/.starcluster/config
    [q] Quit

    Please enter your selection:

Select the second option by typing *2* and pressing enter. This will give you a
template to use to create a configuration file containing your AWS credentials,
cluster settings, etc.  The next step is to customize this file using your
favorite text-editor::

    $ vi ~/.starcluster/config

This file is commented with example "cluster templates". A cluster template
defines a set of configuration settings used to start a new cluster. The
example config provides a *smallcluster* template that is ready to go
out-of-the-box. However, first, you must fill in your AWS credentials and
keypair info::

    [aws info]
    aws_access_key_id = #your aws access key id here
    aws_secret_access_key = #your secret aws access key here
    aws_user_id = #your 12-digit aws user id here

The next step is to fill in your keypair information. If you don't already have
a keypair you can create one from StarCluster using::

    $ starcluster createkey mykey -o ~/.ssh/mykey.rsa

This will create a keypair called *mykey* on Amazon EC2 and save the private
key to ~/.ssh/mykey.rsa.  Once you have a key the next step is to fill-in your
keypair info in the StarCluster config file::

    [key key-name-here]
    key_location = /path/to/your/keypair.rsa

For example, the section for the keypair created above using the **createkey**
command would look like::

    [key mykey]
    key_location = ~/.ssh/mykey.rsa

After defining your keypair in the config, the next step is to update the
default cluster template *smallcluster* with the name of your keypair on EC2::

    [cluster smallcluster]
    keyname = key-name-here

For example, the *smallcluster* template would be updated to look like::

    [cluster smallcluster]
    keyname = mykey

Now that the config file has been set up we're ready to start using
StarCluster. Next we start a cluster named "mycluster" using the default
cluster template *smallcluster* in the example config::

    $ starcluster start mycluster

The *default_template* setting in the **[global]** section of the config
specifies the default cluster template and is automatically set to
*smallcluster* in the example config.

After the **start** command completes you should now have a working cluster.
You can login to the master node as root by running::

    $ starcluster sshmaster mycluster

You can also copy files to/from the cluster using the **put** and **get**
commands.  To copy a file or entire directory from your local computer to the
cluster::

    $ starcluster put mycluster /path/to/local/file/or/dir /remote/path/

To copy a file or an entire directory from the cluster to your local computer::

    $ starcluster get mycluster /path/to/remote/file/or/dir /local/path/

Once you've finished using the cluster and wish to stop paying for it::

    $ starcluster terminate mycluster

Have a look at the rest of StarCluster's available commands::

    $ starcluster --help

Dependencies:
=============
* Amazon AWS Account
* Python 2.6+
* Boto 2.23.0+
* Paramiko 1.12.1+
* WorkerPool 0.9.2
* Jinja2 2.7
* decorator 3.4.0+
* iptools 0.6.1+
* optcomplete 1.2-devel+
* PyCrypto 2.5+
* scp 0.7.1+
* iso8601 0.1.8+

Learn more...
=============
Watch an ~8 minute screencast @ http://star.mit.edu/cluster

To learn more have a look at the documentation:
http://star.mit.edu/cluster/docs/latest

Community
=========
StarCluster has a mailing list for users and developers:

http://star.mit.edu/cluster/mailinglist.html

Join our IRC channel #starcluster on freenode. If you do not have an IRC client
you can join the #starcluster channel using your web browser:

http://webchat.freenode.net/?channels=starcluster

Licensing
=========
StarCluster is licensed under the LGPLv3
See COPYING.LESSER (LGPL) and COPYING (GPL) for LICENSE details

vanilla_improvements branch notes
=============
This branch intends to be a mirror of https://github.com/jtriley/StarCluster develop with more features.

* Added commands
    - printconfig - To print your existing cluster configuration
    - cleancluster
        + Will clean Open Grid Engine from dead nodes. (Eg.: Dead spot instances)
        + Manages "impaired" nodes. (Reboots reserved instances, kills spot instances.)
      (Useful with spot instances and used by the vanilla_improvements load balancer)
    - recover
        + If sge_qmaster crashed, restarts it.
        + If a newly created instance failed to initialize (it's booted but not properly configured in OGS) 
          the instance will be added back to the cluster.
* Improved load balancer
    - More stable with spot instances with automatic cleaning, required when a spot instance dies. Note that 
      stuck jobs resulting in a dead instance are killed by the clean command. You will need to relaunch your job.
    - loadbalance new flags
        + --ignore-grp Instances won't have the placement group constraint. When using spot instances, it makes it easier
          to get instances at a lower price.
        + --reboot-interval - Delay in minutes beyond which a node is rebooted if it's still being unreachable via SSH. 
          Defaults to 10.
        + --num_reboot_restart - Number of reboots after which a node is restarted (stop/start). Helpful in case the 
          issue comes from the hardware. If the node is a spot instance, it will be terminated instead since it cannot 
          be stopped. Defaults to false.
* Improved node cleanup - Merged `robbyt`_ `pull request`_ which makes node cleanup faster.
* Improved node addition - Removed some remote read/writes (very slow) and replaced them get/edit/push.
* Support for multiple subnets - Via the cluster template, allows to get spot instances in the cheapest zone.
  Dropped the --subnet-id start command flag.
* Adds a mode where the cluster configuration is written to master:/etc/starcluster. To activate, simply add flag 
  "--config-on-master" to the start command. Clusters in this mode have the following pros and cons.
  
  - Pros
      + Allows to easily update the config by editing the file.
      + No more obscure update config compressed/hashed data in metadata/tags and other "obscure" places.
  - Cons
      + No longer possible to start a stopped cluster via StarCluster. (This is technically fixable, but not planned at the moment.)
* Adds a --dns-sufix flag to the start command. (`Commit 72f3bc`_)
.. _robbyt: https://github.com/robbyt 
.. _pull request: https://github.com/jtriley/StarCluster/pull/123
.. _Commit 72f3bc: https://github.com/datacratic/StarCluster/commit/72f3bc5ddb028a675f49f3d792c74f6bd3cd1961
