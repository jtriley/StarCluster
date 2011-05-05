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

Amazon EC2 Regions
------------------
StarCluster uses the us-east-1 EC2 region by default. If you wish to use a different EC2 region you will need to specify the following
additional settings in your **[aws info]** section:

.. code-block:: ini

    [aws info]
    ....
    aws_region_name = eu-west-1
    aws_region_host = ec2.eu-west-1.amazonaws.com

Here *aws_region_name* is the name of the region you wish to use and *aws_region_host* is the region-specific EC2 endpoint host. Below is
a table of EC2 region-specific endpoints:

=====================  ==================================
aws_region_name        aws_region_host                   
=====================  ==================================
us-east-1              ec2.us-east-1.amazonaws.com       
us-west-1              ec2.us-west-1.amazonaws.com       
eu-west-1              ec2.eu-west-1.amazonaws.com       
ap-southeast-1         ec2.ap-southeast-1.amazonaws.com  
=====================  ==================================

.. _list: http://developer.amazonwebservices.com/connect/entry.jspa?externalID=3912 

The above table is only for convenience. You will likely want to check the official list_ from Amazon instead.

Amazon S3 Region-Specific Endpoints
-----------------------------------
StarCluster uses s3.amazonaws.com as the S3 endpoint by default. If you'd like to switch S3 endpoints you can do so by specifying an 
additional *aws_s3_host* setting in your **[aws info]** section:

.. code-block:: ini

    [aws info]
    ....
    aws_region_name = us-west-1
    aws_region_name = ec2.us-west-1.amazonaws.com
    aws_s3_host = s3-us-west-1.amazonaws.com

.. _amazon: http://developer.amazonwebservices.com/connect/entry.jspa?externalID=3912

Below is a table of S3 region-specific endpoints:

================  =================================
Region            aws_s3_host                      
================  =================================
us-east-1         s3.amazonaws.com                 
us-west-1         s3-us-west-1.amazonaws.com       
eu-west-1         s3-eu-west-1.amazonaws.com       
ap-southeast-1    s3-ap-southeast-1.amazonaws.com  
================  =================================

**NOTE**: Switching S3 endpoints is usually not necessary. From amazon_: Switching to a region-specific S3 endpoint is completely optional. 
The main advantage of doing so is to reduce the temporary latency you might experience immediately after creating a bucket in a specific region.
This temporary latency typically lasts less than one hour.

Amazon EC2 Keypairs
-------------------
In addition to supplying your **[aws info]** you must also define at least one **[keypair]** section that
represents one of your keypairs on Amazon EC2. Amazon EC2 keypairs are used by StarCluster to connect and configure your 
instances.

You should define a new **[keypair]** section for each Amazon EC2 keypair you wish to use with StarCluster.  
As an example, suppose we have two keypairs on Amazon EC2 that we wish to use with StarCluster named "mykeypair1" 
and "mykeypair2" on Amazon. 

**NOTE**: If you do not know the name of your keypair(s), use StarCluster's *listkeypairs* command or the *ec2-describe-keypairs* 
command in the EC2 command line tools. The **[keypair]** section name *must* match the name of the keypair on Amazon EC2.

To configure StarCluster for these keypairs we define a **[keypair]** section for each of them in the configuration file:

.. code-block:: ini

    [keypair mykeypair1]
    # this is the path to your openssh private key for mykeypair4
    key_location=/path/to/your/mykeypair1.rsa

    [keypair mykeypair3]
    # this is the path to your openssh private key for mykeypair2
    key_location=/path/to/your/mykeypair2.rsa

These keypair sections can now be referenced in a *cluster templates*' **keyname** setting as we'll show below in an
example *cluster template*.

**NOTE**: In order for StarCluster to interact with **any** instances you have on EC2, the keypair used to launch those instances 
**must** be defined in the config. You can check what keypairs were used to launch an instance using StarCluster's *listinstances* 
command or the *ec2-describe-instances* command from the ec2 command-line tools.

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

    # instance type for master node. 
    # defaults to NODE_INSTANCE_TYPE if not specified
    master_instance_type = m1.small

    # AMI for worker nodes. 
    # Also used for the master node if MASTER_IMAGE_ID is not specified
    # The base i386 StarCluster AMI is ami-0330d16a
    # The base x86_64 StarCluster AMI is ami-0f30d166
    node_image_id = ami-0330d16a

    # instance type for worker nodes. Also used for the master node if 
    # MASTER_INSTANCE_TYPE is not specified
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
    #...
    volumes = myvoldata1, myvoldata2
    #...

Now any time a cluster is started using the *smallcluster* template, myvoldata1 will be mounted to /home on the master, myvoldata2 will
be mounted to /scratch on the master, and both /home and /scratch will be NFS shared to the rest of the cluster nodes. 

Amazon Security Group Permissions
---------------------------------
When starting a cluster each node is added to a common security group. This security group is created by StarCluster and has  
a name of the form "@sc-*<cluster_tag>*" where *<cluster_tag>* is the name you provided to the "start" command.

By default, StarCluster adds a permission to this security group that allows access to port 22 (openssh) from all IP addresses. This is needed
so that StarCluster can connect to the instances and configure them properly. If you want to specify additional security group permissions to be 
set after starting your cluster you can do so in the config by creating one or more **[permission]** sections. These sections can then be specified
in one or more cluster templates. Here's an example that opens port 80 (web server) to the world for the *smallcluster* template:

.. code-block:: ini

    [permission www]
    # open port 80 to the world
    from_port = 80
    to_port = 80
    
    [permission ftp]
    # open port 21 only to a single ip
    from_port = 21
    to_port = 21
    cidr_ip = 66.249.90.104/32

    [permission myrange]
    # open all ports in the range 8000-9000 to the world
    from_port = 8000
    to_port = 9000

    [cluster smallcluster]
    #...
    permissions = www, ftp, myrange
    #...

A permission section specifies a port range to open to a given network range (cidr_ip). By default, the network range is set to 0.0.0.0/0 which represents any 
ip address (ie the "world"). In the above example, we created a permission section called *www* that opens port 80 to the "world" by setting the from_port 
and to_port both to be 80.  You can restrict the ip addresses that the rule applies to by specifying the proper cidr_ip setting. In the above example, 
the *ftp* permission specifies that only 66.249.90.104 ip address can access port 21 on the cluster nodes. 

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
