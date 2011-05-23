Quick-Start
===========

Install StarCluster using easy_install::

    $ sudo easy_install StarCluster

or to install StarCluster manually::

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
settings used to start a new cluster. The example config provides a 'smallcluster' template that is
ready to go out-of-the-box. However, first, you must fill in your AWS credentials and keypair info:

.. code-block:: ini

    [aws info]
    aws_access_key_id = #your aws access key id here
    aws_secret_access_key = #your secret aws access key here
    aws_user_id = #your 12-digit aws user id here

The next step is to fill in your keypair information. If you don't already have a keypair you can create one from StarCluster using: ::

    $ starcluster createkey mykey -o ~/.ssh/mykey.rsa

This will create a keypair called 'mykey' on Amazon EC2 and save the private key to ~/.ssh/mykey.rsa.
Once you have a key the next step is to fill-in your keypair info in the StarCluster config file:

.. code-block:: ini

    [key key-name-here]
    key_location = /path/to/your/keypair.rsa

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
