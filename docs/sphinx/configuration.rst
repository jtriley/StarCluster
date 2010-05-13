******************************
StarCluster Configuration File
******************************
The StarCluster configuration file uses ini formatting (see http://en.wikipedia.org/wiki/INI_file). 
It is made up of various sections which are described in detail here. This document explains how 
to configure the three required sections **[aws info]**, **[keypair]**, and **[cluster]** as well as
optional **[global]**, **[volume]**, and **[plugin]** sections.

Creating the config file
------------------------
The default starcluster config lives in ~/.starcluster/config. You can either create this file manually
or have starcluster create it for you with an example configuration template (recommended).

To have StarCluster generate an example configuration file (~/.starcluster/config), simply run "starcluster help"
at the command-line. Provided that the configuration file does not exist, you will see the following:

.. code-block:: none

    user@localhost$ starcluster help
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    cli.py:475 - ERROR - Config file /home/user/.starcluster/config does not exist

    Options:
    --------
    [1] Show the StarCluster config template
    [2] Write config template to /home/user/.starcluster/config
    [q] Quit
    
    Plase enter your selection:  

Selecting 1 will print the example configuration file template to standard output.

Selecting 2 will write the configuration file template to ~/.starcluster/config

The configuration template provided by StarCluster should be ready to go out-of-the-box after filling in your Amazon Web
Services credentials and setting up a keypair. This example config provides a simple *cluster template* called 'smallcluster'.
This 'smallcluster' template is also set as the default *cluster template*. The following sections explain each section of the 
config and their options.

Amazon Web Services Credentials
-------------------------------
The first required section in the configuration file is **[aws info]**. This section specifies all of your
AWS credentials. The following settings are required

.. code-block:: ini

    [aws info]
    # replace these with your AWS keys (required)
    aws_access_key_id = #your_aws_access_key_id
    aws_secret_access_key = #your_secret_access_key
    # these settings are optional and only used for creating new AMIs
    aws_user_id= #your userid
    ec2_cert = /path/to/your/ec2_cert.pem
    ec2_private_key = /path/to/your/ec2_pk.pem

Amazon EC2 Keypairs
-------------------
In addition to supplying your **[aws info]** you must also define at least one **[keypair]** section that
represents one of your keypairs on Amazon EC2. You can also define a new **[keypair]** section for each Amazon EC2
keypair you want to use with StarCluster. 

As an example, suppose we have two keypairs on Amazon EC2 that we wish to use with StarCluster called "mykeypair1" 
and "mykeypair2".  To configure StarCluster for these keypairs we define a **[keypair]** section for each of them 
in the configuration file:

.. code-block:: ini

    [keypair mykeypair1]
    # this is the path to your openssh private key for mykeypair1
    key_location=/path/to/your/mykeypair1.rsa

    [keypair mykeypair2]
    # this is the path to your openssh private key for mykeypair2
    key_location=/path/to/your/mykeypair2.rsa

These keypair sections can now be referenced in a *cluster templates*' **keyname** setting as we'll show below in an
example *cluster template*.

Defining Cluster Templates
--------------------------
In order to launch StarCluster(s) on Amazon EC2, you must first provide a *cluster template* that contains all of the 
configuration for the cluster. A *cluster template* is simply a **[cluster]** section in the config. Once a *cluster 
template* has been defined, you can launch multiple StarClusters from it. Below is an example *cluster template* called
'smallcluster' which defines a 2-node cluster using *m1.small* EC2 instances and the mykeypair1 keypair we defined above.

.. code-block:: ini

    # Sections starting with "cluster" define your cluster templates
    # The section name is the name you give to your cluster template e.g.:
    [cluster smallcluster]
    # change this to the name of one of the keypair sections defined above 
    # (see the EC2 getting started guide tutorial on using ec2-add-keypair to learn
    # how to create new keypairs)
    keyname = mykeypair1

    # number of ec2 instances to launch
    cluster_size = 2

    # create the following user on the cluster
    cluster_user = sgeadmin
    # optionally specify shell (defaults to bash)
    # options: bash, zsh, csh, ksh, tcsh
    cluster_shell = bash

    # AMI for master node. Defaults to NODE_IMAGE_ID if not specified
    # The base i386 StarCluster AMI is ami-0330d16a
    # The base x86_64 StarCluster AMI is ami-0f30d166
    master_image_id = ami-0330d16a
    # instance type for master node
    master_instance_type = m1.small

    # AMI for worker nodes. Also used for the master node if MASTER_IMAGE_ID is not specified
    # The base i386 StarCluster AMI is ami-0330d16a
    # The base x86_64 StarCluster AMI is ami-0f30d166
    node_image_id = ami-0330d16a

    # instance type
    node_instance_type = m1.small

    # availability zone
    availability_zone = us-east-1c

Defining Multiple Cluster Templates
-----------------------------------
You are not limited to defining just one *cluster template*. StarCluster allows you to define multiple independent cluster
templates by simply creating a new **[cluster]** section with all of the same settings (different values of course).

However, you may find that defining new *cluster templates* is some what repetitive with respect to redefining the same 
settings over and over. To remedy this situation, StarCluster allows *cluster templates* to extend other *cluster 
templates*:

.. code-block:: ini

    [cluster mediumcluster]
    # Declares that this cluster uses smallcluster's settings as defaults
    extends = smallcluster
    # this rest of this section is identical to smallcluster except for the following settings:
    keyname = mykeypair2
    node_instance_type = c1.xlarge
    cluster_size = 8
    volumes = biodata2

In the example above, *mediumcluster* will use all of *smallcluster*'s settings as defaults. All other settings in the *mediumcluster*
template override these defaults. For the *mediumcluster* template above, we can see that *mediumcluster* is the same as *smallcluster*
except for its keyname, node_instance_type, cluster_size, and volumes settings.

Setting the Default Cluster Template
------------------------------------
StarCluster allows you to specify a default *cluster template* to be used when using the "start" command. This is useful for
users that mostly use a single *cluster template*. To define a default *cluster template*, define a **[global]** section and 
configure the **default_template** setting:

.. code-block:: ini

    [global]
    default_template = smallcluster

The above example sets the 'smallcluster' *cluster template* as the default.

Amazon EBS Volumes
------------------
StarCluster has the ability to use Amazon EBS volumes to provide persistent data storage on a given cluster. If you wish to use 
EBS volumes with StarCluster you will need to define a **[volume]** section in the configuration file for each volume you wish to 
use with StarCluster and then add this **[volume]** section name to a *cluster template*'s **volumes** setting. Please note that 
using EBS volumes with StarCluster is completely optional. If you do not wish to use EBS volumes with StarCluster, simply do not 
define any **[volume]** sections and remove or comment-out the **volumes** setting from your *cluster template(s)*.

However, if you do not use an EBS volume with StarCluster, any data that you wish to keep around after shutdown 
must be manually copied somewhere outside of the cluster (e.g. download the data locally or move it to S3 manually). This is because
local instance storage on EC2 is ephemeral and does not persist after an instance has been shutdown. The advantage of using EBS 
volumes with StarCluster is that when you shutdown a particular cluster, any data saved on an EBS volume attached to that cluster 
will be available the next time the volume is attached to another cluster (or EC2 instance). 

To configure an EBS volume for use with Starcluster, define a new **[volume]** section for each EBS volume. For example, suppose
we have two volumes we'd like to use: vol-c9999999 and vol-c8888888. Below is an example configuration for these volumes:

.. code-block:: ini

    [volume myvoldata1]
    # this is the Amazon EBS volume id
    volume_id=vol-c9999999
    # the path to mount this EBS volume on
    # (this path will also be nfs shared to all nodes in the cluster)
    mount_path=/home

    [volume myvoldata2]
    volume_id=vol-c8888888
    mount_path=/scratch

    [volume myvoldata2-alternate]
    # same volume as myvoldata2 but uses 2nd partition instead of 1st
    volume_id=vol-c8888888
    mount_path=/scratch2
    partition=2

StarCluster by default attempts to mount the first partition in the volume onto the master node. It is possible to use a different 
partition by configuring a **partition** setting in your **[volume]** section as in the *myvoldata2-alternate* example above.

After defininig one or more **[volume]** sections, you then need to add them to a *cluster template* in order to use them. To do this,
specify the **[volume]** section name(s) in the **volumes** setting in one or more of your *cluster templates*. For example, to use both 
myvoldata1 and myvoldata2 from the above example in a *cluster template* called *smallcluster*:

.. code-block:: ini

    [cluster smallcluster]
    ...
    volumes = myvoldata1, myvoldata2
    ...

Now any time a cluster is started using the *smallcluster* template, myvoldata1 will be mounted to /home on the master, myvoldata2 will
be mounted to /scratch on the master, and both /home and /scratch will be NFS shared to the rest of the cluster nodes. 

StarCluster Plugins
-------------------
StarCluster also has support for user contributed plugins (see :doc:`plugins`).  To configure a *cluster template* to use a particular 
plugin, we must first create a plugin section for each plugin we wish to use. For example, suppose we have two plugins myplug1 and myplug2:

.. code-block:: ini

    [plugin myplug1]
    setup_class = myplug1.SetupClass
    myplug1_arg_one = 2

    [plugin myplug2]
    setup_class = myplug2.SetupClass
    myplug2_arg_one = 3

In this example, myplug{1,2}_arg_one are arguments to the plugin's *setup_class*. The 'myplug{1,2}_arg_one' variable names were made up 
for this example.  The names of these arguments depend on the plugin being used. Some plugins may not even have arguments. 

After you've defined some **[plugin]** sections, you can reference them in a *cluster template* like so:

.. code-block:: ini

    [cluster mediumcluster]
    # Declares that this cluster uses smallcluster's settings as defaults
    extends = smallcluster
    # this rest of this section is identical to smallcluster except for the following settings:
    keyname = mykeypair2
    node_instance_type = c1.xlarge
    cluster_size = 8
    volumes = biodata2
    plugins = myplug1, myplug2

Notice the added *plugins* setting for the 'mediumcluster' template. This setting instructs StarCluster to first run the 'myplug1' plugin 
and then the 'myplug2' plugin afterwards. Reversing myplug1/myplug2 in the plugins setting in the above example would reverse the order 
of execution.
