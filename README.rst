===================
StarCluster v0.92.1
===================
:StarCluster: Cluster Computing Toolkit for the Cloud
:Version: 0.92.1
:Author: Justin Riley <justin.t.riley@gmail.com>
:Team: Software Tools for Academics and Researchers (http://web.mit.edu/star)
:Homepage: http://web.mit.edu/starcluster
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
* **Automated Cluster Setup** - includes NFS-sharing, Sun Grid Engine queuing
  system, password-less ssh between machines, and more
* **Scientific Computing AMI** - contains OpenMPI, ATLAS, Lapack, NumPy, SciPy,
  and other useful libraries
* **EBS Volume Sharing** - easily NFS-share Amazon Elastic Block Storage (EBS)
  volumes across a cluster for persistent storage
* **EBS-Backed Clusters** - start and stop EBS-backed clusters on EC2
* **Cluster Compute Instances** - support for "cluster compute" instance types
* **Add/Remove Nodes** - scale a cluster by adding or removing nodes
* **Elastic Load Balancing** - automatically shrink or expand a cluster based
  on Sun Grid Engine queue statistics
* **Plugin Support** - allows users to run additional setup routines on the
  cluster after StarCluster's defaults by writing simple plugins in Python
* and more...

Interested? See the `getting started`_ section for more details.

.. _getting started:

Getting Started:
================
Install StarCluster using easy_install::

    $ sudo easy_install StarCluster

or to install StarCluster manually::

    $ (Download StarCluster from http://web.mit.edu/starcluster)
    $ tar xvzf starcluster-X.X.X.tar.gz  (where x.x.x is a version number)
    $ cd starcluster-X.X.X
    $ sudo python setup.py install

After the software has been installed, the next step is to setup the
configuration file::

    $ starcluster help
    StarCluster - (http://web.mit.edu/starcluster) (v. 0.9999)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    cli.py:87 - ERROR - config file /home/user/.starcluster/config does not exist

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
keypair info:

.. code-block:: ini

    [aws info]
    aws_access_key_id = #your aws access key id here
    aws_secret_access_key = #your secret aws access key here
    aws_user_id = #your 12-digit aws user id here

The next step is to fill in your keypair information. If you don't already have
a keypair you can create one from StarCluster using::

    $ starcluster createkey mykey -o ~/.ssh/mykey.rsa

This will create a keypair called *mykey* on Amazon EC2 and save the private
key to ~/.ssh/mykey.rsa.  Once you have a key the next step is to fill-in your
keypair info in the StarCluster config file:

.. code-block:: ini

    [key key-name-here]
    key_location = /path/to/your/keypair.rsa

For example, the section for the keypair created above using the **createkey**
command would look like:

.. code-block:: ini

    [key mykey]
    key_location = ~/.ssh/mykey.rsa

After defining your keypair in the config, the next step is to update the
default cluster template *smallcluster* with the name of your keypair on EC2:

.. code-block:: ini

    [cluster smallcluster]
    keyname = key-name-here

For example, the *smallcluster* template would be updated to look like:

.. code-block:: ini

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

    $ starcluster put /path/to/local/file/or/dir /remote/path/

To copy a file or an entire directory from the cluster to your local computer::

    $ starcluster get /path/to/remote/file/or/dir /local/path/

Once you've finished using the cluster and wish to stop paying for it::

    $ starcluster terminate mycluster

Have a look at the rest of StarCluster's available commands::

    $ starcluster --help

Dependencies:
=============
* Amazon AWS Account
* Python 2.5+
* Boto 2.0
* Paramiko 1.7.7.1
* WorkerPool 0.9.2
* Jinja2 2.5.5
* decorator 3.3.1

Learn more...
=============
Watch an ~8 minute screencast @ http://web.mit.edu/starcluster

To learn more have a look at the documentation:
http://web.mit.edu/starcluster/docs/latest

Licensing
=========
StarCluster is licensed under the LGPLv3
See COPYING.LESSER (LGPL) and COPYING (GPL) for LICENSE details

What's New?
===========
See http://web.mit.edu/starcluster/docs/latest/changelog.html for the full
version history.

Features
--------
* Support for splitting the config into an arbitrary set of files::

    [global]
    include=~/.starcluster/awscreds, ~/.starcluster/myconf

  See `Splitting the Config`_ for more details

* createvolume: support naming/tagging newly created volumes::

    $ starcluster createvolume --name mynewvol 30 us-east-1d

  See `Create and Format a new EBS Volume` for more details

* listvolumes: add support for filtering by tags::

    $ starcluster listvolumes --name mynewvol
    $ starcluster listvolumes --tag mykey=myvalue

  See `Managing EBS Volumes with StarCluster`_ for more details

* sshmaster, sshnode, sshinstance: support for running remote
  commands from command line::

    $ starcluster sshmaster mycluster 'cat /etc/fstab'
    $ starcluster sshnode mycluster node001 'cat /etc/fstab'
    $ starcluster sshinstance i-99999999 'cat /etc/hosts'

  See `Running Remote Commands on a Cluster from Command Line`_ for more
  details

Bug Fixes
---------
The following bugs were fixed in this release:

**spothistory command**

* add package_data to sdist in order to include the necessary web media and
  templates needed for the ``--plot`` feature. The previous 0.92 version left
  these out and thus the ``--plot`` feature was broken. This should be fixed.
* fix bug when launching default browser on mac

**start command**

* fix bug in option completion when using the start command's
  ``--cluster-template`` option

**terminate command**

* fix bug in terminate cmd when region != us-east-1

**listkeypairs command**

* fix bug in list_keypairs when no keys exist

Improvements
------------
* listinstances: add 'state_reason' msg to output if available
* add system info, Python info, and package versions to crash-report
* listregions: sort regions by name
* improved bash/zsh completion support. completion will read from the correct
  config file, if possible, in the case that the global -c option is specified
  while completing.
* separate the timing of cluster setup into time spent on waiting for EC2
  instances to come up and time spent configuring the cluster after all
  instances are up and running. this is useful when profiling StarCluster's
  performance on large (100+ node) clusters.

.. _Splitting the Config: http://web.mit.edu/starcluster/docs/latest/manual/configuration.html#splitting-the-config

.. _Create and Format a new EBS Volume: http://web.mit.edu/starcluster/docs/latest/manual/volumes.html#create-and-format-ebs-volumes

.. _Managing EBS Volumes with StarCluster: http://web.mit.edu/starcluster/docs/latest/manual/volumes.html#managing-ebs-volumes

.. _Running Remote Commands on a Cluster from Command Line: http://web.mit.edu/starcluster/docs/latest/manual/runcommands.html
