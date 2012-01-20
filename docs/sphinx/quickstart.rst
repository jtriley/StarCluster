Quick-Start
===========

.. note::

    These instructions are meant to get users up and running quickly without
    going through all of the steps in detail. For more information please refer
    to the full :ref:`user manual <starcluster-user-manual>`.

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

Learn more...
-------------
Watch an ~8min screencast @ http://web.mit.edu/stardev/cluster

To learn more have a look at the rest of the documentation:
http://web.mit.edu/stardev/cluster/docs

The docs explain the configuration file in detail, how to create/use EBS
volumes with StarCluster, how to use the Sun Grid Engine queueing system to
submit jobs on the cluster, using and creating plugins, and much more.
