******************************
StarCluster Configuration File
******************************
The StarCluster configuration file uses `ini formatting
<http://en.wikipedia.org/wiki/INI_file>`_. It is made up of various sections
which are described here in detail. This document explains how to configure the
three required sections **[aws info]**, **[keypair]**, and **[cluster]** as
well as optional **[global]**, **[volume]**, **[permission]**, and **[plugin]**
sections.

Creating the configuration file
-------------------------------
The default starcluster config lives in ``~/.starcluster/config``. You can
either create this file manually or have starcluster create it for you with an
example configuration template (recommended).

To have StarCluster generate an example configuration file at the default
config location (``~/.starcluster/config``), simply run "starcluster help" at
the command-line.  Provided that the configuration file does not exist, you
will see the following::

    $ starcluster help
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    cli.py:475 - ERROR - Config file /home/user/.starcluster/config does not exist

    Options:
    --------
    [1] Show the StarCluster config template
    [2] Write config template to /home/user/.starcluster/config
    [q] Quit

    Please enter your selection:

Selecting 1 will print the example configuration file template to standard
output.

Selecting 2 will write the configuration file template to ~/.starcluster/config

The configuration template provided by StarCluster should be ready to go
out-of-the-box after filling in your Amazon Web Services credentials and
setting up a keypair. This example config provides a simple *cluster template*
called ``smallcluster`` that is set as the default *cluster template*.

Storing the config in an alternate location
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you wish to store your StarCluster config in a location other than the
default (``~/.starcluster/config``) you will need to specify the global
``--config`` (``-c``) option with every StarCluster command you use. For
example::

    $ starcluster -c /path/to/starcluster/config listclusters

In the above example, if the config didn't exist at the specified path you
would be prompted with the same menu above offering to generate a template at
the specified path::

    $ starcluster -c /path/to/nonexistent/config listclusters
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    cli.py:475 - ERROR - Config file /path/to/nonexistent/config does not exist

    Options:
    --------
    [1] Show the StarCluster config template
    [2] Write config template to /path/to/nonexistent/config
    [q] Quit

    Please enter your selection:

Loading the config from the web
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The config can also be loaded from a web url, however, if you choose to do so
you should be *very* careful not to publicly host AWS credentials, keys, and
other private information::

    $ starcluster -c http://localhost/starcluster.cfg listclusters

.. seealso::

    See also: :ref:`splitting-the-config`

Amazon Web Services Credentials
-------------------------------
The first required section in the configuration file is **[aws info]**. This
section specifies all of your AWS credentials. The following settings are
required:

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
StarCluster uses the us-east-1 EC2 region by default. If you wish to
permanently use a different EC2 region you will need to specify the following
additional settings in your **[aws info]** section:

.. code-block:: ini

    [aws info]
    aws_region_name = eu-west-1
    aws_region_host = ec2.eu-west-1.amazonaws.com

Here ``aws_region_name`` is the name of the region you wish to use and
``aws_region_host`` is the region-specific EC2 endpoint host. Below is a table of
EC2 region-specific endpoints:

=====================  ==================================
aws_region_name        aws_region_host
=====================  ==================================
us-east-1              ec2.us-east-1.amazonaws.com
us-west-1              ec2.us-west-1.amazonaws.com
eu-west-1              ec2.eu-west-1.amazonaws.com
ap-southeast-1         ec2.ap-southeast-1.amazonaws.com
ap-northeast-1         ec2.ap-northeast-1.amazonaws.com
=====================  ==================================

.. _list from Amazon: http://docs.amazonwebservices.com/general/latest/gr/rande.html#ec2_region

The above table is only for convenience. In practice you should use the
official `list from Amazon`_ instead.

Switching Regions via Command Line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
StarCluster also supports quickly switching between EC2 regions via the command
line without having to change your config. To switch regions at the command
line use the global *-r* (*--region*) option::

    $ starcluster -r us-west-1 listpublic

The above example runs the **listpublic** command in the ``us-west-1`` region.
Similarly, you will need to pass the global *-r* option to all of StarCluster's
commands in order to switch regions via the command line.

.. seealso::

    See also: :ref:`tips-for-switching-regions`

Amazon S3 Region-Specific Endpoints
-----------------------------------
.. _amazon: http://aws.amazon.com/articles/3912
.. note::

   Switching S3 endpoints is usually not necessary. From amazon_: Switching to
   a region-specific S3 endpoint is completely optional.  The main advantage of
   doing so is to reduce the temporary latency you might experience immediately
   after creating a bucket in a specific region.  This temporary latency
   typically lasts less than one hour.

StarCluster uses s3.amazonaws.com as the S3 endpoint by default. If you'd like
to switch S3 endpoints you can do so by specifying an additional
``aws_s3_host`` setting in your **[aws info]** section:

.. code-block:: ini

    [aws info]
    aws_region_name = us-west-1
    aws_region_name = ec2.us-west-1.amazonaws.com
    aws_s3_host = s3-us-west-1.amazonaws.com

Below is a table of S3 region-specific endpoints:

================  =================================
Region            aws_s3_host
================  =================================
us-east-1         s3.amazonaws.com
us-west-1         s3-us-west-1.amazonaws.com
eu-west-1         s3-eu-west-1.amazonaws.com
ap-southeast-1    s3-ap-southeast-1.amazonaws.com
ap-northeast-1    s3-ap-northeast-1.amazonaws.com
================  =================================

.. _proxy-config:

Using a Proxy Host
------------------
StarCluster can also be configured to use a proxy host when connecting to AWS
by specifying the following settings in your **[aws info]** section:

**aws_proxy** - The name of the proxy host to use for connecting to AWS.

**aws_proxy_port** - The port number to use to connect to the proxy host.

**aws_proxy_user** - The user name to use when authenticating with proxy host.

**aws_proxy_pass** - The password to use when authenticating with proxy host.

.. _boto: http://github.com/boto/boto

StarCluster will use the settings above when creating the `boto`_ connection
object used to communicate with AWS. Example:

.. code-block:: ini

   [aws info]
   aws_proxy = your.proxyhost.com
   aws_proxy_port = 8080
   aws_proxy_user = yourproxyuser
   aws_proxy_pass = yourproxypass

Amazon EC2 Keypairs
-------------------
In addition to supplying your **[aws info]** you must also define at least one
**[keypair]** section that represents one of your keypairs on Amazon EC2.
Amazon EC2 keypairs are used by StarCluster to connect and configure your
instances.

You should define a new **[keypair]** section for each Amazon EC2 keypair you
wish to use with StarCluster.  As an example, suppose we have two keypairs on
Amazon EC2 that we wish to use with StarCluster named ``mykeypair1`` and
``mykeypair2`` on Amazon.

.. note::

   If you do not know the name of your keypair(s), use StarCluster's
   **listkeypairs** command to obtain a list of your current EC2 keypairs. The
   **[keypair]** section name *must* match the name of the keypair on Amazon
   EC2.

To configure StarCluster for these keypairs we define a **[keypair]** section
for each of them in the configuration file:

.. code-block:: ini

    [keypair mykeypair1]
    # this is the path to your openssh private key for mykeypair4
    key_location=/path/to/your/mykeypair1.rsa

    [keypair mykeypair3]
    # this is the path to your openssh private key for mykeypair2
    key_location=/path/to/your/mykeypair2.rsa

These keypair sections can now be referenced in a *cluster template's*
**keyname** setting as we'll :ref:`show below <defining-cluster-templates>` in
an example *cluster template*.

.. _AWS web console: http://aws.amazon.com/console

.. note::

   In order for StarCluster to interact with *any* instances you have on EC2,
   the keypair used to launch those instances *must* be defined in the
   config. You can check what keypairs were used to launch an instance using
   StarCluster's **listinstances** command or the `AWS web console`_.

.. _defining-cluster-templates:

Defining Cluster Templates
--------------------------
In order to launch StarCluster(s) on Amazon EC2, you must first provide a
*cluster template* that contains all of the configuration for the cluster. A
*cluster template* is simply a **[cluster]** section in the config. Once a
*cluster template* has been defined, you can launch multiple StarClusters from
it. Below is an example *cluster template* called ``smallcluster`` which
defines a 2-node cluster using ``m1.small`` EC2 instances and the mykeypair1
keypair we defined above.

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
You are not limited to defining just one *cluster template*. StarCluster allows
you to define multiple independent cluster templates by simply creating a new
**[cluster]** section with all of the same settings (different values of
course).

However, you may find that defining new *cluster templates* is some what
repetitive with respect to redefining the same settings over and over. To
remedy this situation, StarCluster allows *cluster templates* to extend other
*cluster templates*:

.. code-block:: ini

    [cluster mediumcluster]
    # Declares that this cluster uses smallcluster's settings as defaults
    extends = smallcluster
    # this rest of this section is identical to smallcluster except for the following settings:
    keyname = mykeypair2
    node_instance_type = c1.xlarge
    cluster_size = 8
    volumes = biodata2

In the example above, ``mediumcluster`` will use all of ``smallcluster``'s
settings as defaults. All other settings in the ``mediumcluster`` template
override these defaults. For the ``mediumcluster`` template above, we can see
that ``mediumcluster`` is the same as ``smallcluster`` except for its
``keyname``, ``node_instance_type``, ``cluster_size``, and ``volumes``
settings.

Setting the Default Cluster Template
------------------------------------
StarCluster allows you to specify a default *cluster template* to be used when
using the **start** command. This is useful for users that mostly use a single
*cluster template*. To define a default *cluster template*, define a
**[global]** section and configure the **default_template** setting:

.. code-block:: ini

    [global]
    default_template = smallcluster

The above example sets the ``smallcluster`` *cluster template* as the default.

.. note::

   If you do not specify a default *cluster template* in the config you will
   have to specify one at the command line using the ``--cluster-template``
   (``-c``) option.

Amazon EBS Volumes
------------------

.. warning::
   Using EBS volumes with StarCluster is completely optional, however, if you
   do not use an EBS volume with StarCluster, any data that you wish to keep
   around after shutdown must be manually copied somewhere outside of the
   cluster (e.g. download the data locally or move it to S3 manually).  This is
   because local instance storage on EC2 is ephemeral and does not persist
   after an instance has been terminated. The advantage of using EBS volumes
   with StarCluster is that when you shutdown a particular cluster, any data
   saved on an EBS volume attached to that cluster will be available the next
   time the volume is attached to another cluster or EC2 instance.

StarCluster has the ability to use Amazon EBS volumes to provide persistent
data storage on a given cluster. If you wish to use EBS volumes with
StarCluster you will need to define a **[volume]** section in the configuration
file for each volume you wish to use with StarCluster and then add this
**[volume]** section name to a *cluster template*'s **volumes** setting.

To configure an EBS volume for use with Starcluster, define a new **[volume]**
section for each EBS volume. For example, suppose we have two volumes we'd like
to use: ``vol-c9999999`` and ``vol-c8888888``. Below is an example configuration for
these volumes:

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

StarCluster by default attempts to mount either the entire drive or the first
partition in the volume onto the master node. It is possible to use a different
partition by configuring a **partition** setting in your **[volume]** section
as in the ``myvoldata2-alternate`` example above.

After defining one or more **[volume]** sections, you then need to add them to
a *cluster template* in order to use them. To do this, specify the **[volume]**
section name(s) in the **volumes** setting in one or more of your *cluster
templates*. For example, to use both ``myvoldata1`` and ``myvoldata2`` from the
above example in a *cluster template* called ``smallcluster``:

.. code-block:: ini

    [cluster smallcluster]
    volumes = myvoldata1, myvoldata2

Now any time a cluster is started using the ``smallcluster`` template,
``myvoldata1`` will be mounted to ``/home`` on the master, ``myvoldata2`` will
be mounted to ``/scratch`` on the master, and both ``/home`` and ``/scratch``
will be NFS-shared to the rest of the cluster nodes.

.. seealso::

   See the :doc:`volumes` documentation to learn how to use StarCluster to
   easily create, format, and configure new EBS volumes.

.. _config_permissions:

Amazon Security Group Permissions
---------------------------------
When starting a cluster each node is added to a common security group. This
security group is created by StarCluster and has a name of the form
``@sc-<cluster_tag>`` where ``<cluster_tag>`` is the name you provided to the
**start** command.

By default, StarCluster adds a permission to this security group that allows
access to port 22 (ssh) from all IP addresses. This is needed so that
StarCluster can connect to the instances and configure them properly. If you
want to specify additional security group permissions to be set after starting
your cluster you can do so in the config by creating one or more
**[permission]** sections. These sections can then be specified in one or more
cluster templates. Here's an example that opens port 80 (web server) to the
world for the ``smallcluster`` template:

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
    permissions = www, ftp, myrange

A permission section specifies a port range to open to a given network range
(cidr_ip). By default, the network range is set to ``0.0.0.0/0`` which
represents any ip address (i.e. the "world"). In the above example, we created a
permission section called ``www`` that opens port 80 to the "world" by setting
the from_port and to_port both to be 80.  You can restrict the ip addresses
that the rule applies to by specifying the proper cidr_ip setting. In the above
example, the ``ftp`` permission specifies that only ``66.249.90.104`` ip
address can access port 21 on the cluster nodes.

Defining Plugins
----------------
StarCluster also has support for user contributed plugins (see :doc:`plugins`).
To configure a *cluster template* to use a particular plugin, we must first
create a plugin section for each plugin we wish to use. For example, suppose we
have two plugins ``myplug1`` and ``myplug2``:

.. code-block:: ini

    [plugin myplug1]
    setup_class = myplug1.SetupClass
    myplug1_arg_one = 2

    [plugin myplug2]
    setup_class = myplug2.SetupClass
    myplug2_arg_one = 3

In this example, ``myplug1_arg_one`` and ``myplug2_arg_one`` are arguments to
the plugin's *setup_class*. The argument names were made up for this example.
The names of a plugin's arguments in general depends on the plugin being used.
Some plugins may not even have arguments.

After you've defined some **[plugin]** sections, you can reference them in a
*cluster template* like so:

.. code-block:: ini

    [cluster mediumcluster]
    # Declares that this cluster uses smallcluster's settings as defaults
    extends = smallcluster
    # the rest  is identical to smallcluster except for the following settings:
    keyname = mykeypair2
    node_instance_type = c1.xlarge
    cluster_size = 8
    volumes = biodata2
    plugins = myplug1, myplug2

Notice the added ``plugins`` setting for the ``mediumcluster`` template. This
setting instructs StarCluster to first run the ``myplug1`` plugin and then the
``myplug2`` plugin afterwards. Reversing ``myplug1``/``myplug2`` in the plugins
setting in the above example would reverse the order of execution.

.. seealso::

    Learn more about the :doc:`plugins`

.. _splitting-the-config:

Splitting the Config into Multiple Files
----------------------------------------
In some cases you may wish to split your configuration file into separate files
for convenience. For example, you may wish to organize all keypairs, cluster
templates, permissions, volumes, etc. into separate files to make it easier to
access the relevant settings without browsing the entire config all at once. To
do this, simply create a new set of files and put the relevant config sections
into the files:

.. note::

    The following list of files are just examples. You are free to create any
    number of files, name them anything you want, and distribute any of the
    sections in the config to these files in any way you see fit. The only
    exception is that the **[global]** section *must* live in either the
    default config ``$HOME/.starcluster/config`` or the config specified by the
    global ``--config`` (``-c``) command line option.

**File**: ``$HOME/.starcluster/awskeys``

.. code-block:: ini

    [aws info]
    aws_access_key_id = #your_aws_access_key_id
    aws_secret_access_key = #your_secret_access_key

    [key mykey1]
    key_location=/path/to/key1

    [key mykey2]
    key_location=/path/to/key2

**File**: ``$HOME/.starcluster/clusters``

.. code-block:: ini

    [cluster smallcluster]
    cluster_size = 5
    keyname = mykey1
    node_image_id = ami-99999999

    [cluster largecluster]
    extends = smallcluster
    cluster_size = 50
    node_image_id = ami-88888888

**File**: ``$HOME/.starcluster/vols``

.. code-block:: ini

    [key mykey]
    key_location=/path/to/key

Then define the files in the config using the *include* setting in the
**[global]** section of the default StarCluster config
(``~/.starcluster/config``):

.. code-block:: ini

    [global]
    include = ~/.starcluster/awskeys, ~/.starcluster/clusters, ~/.starcluster/vols

Loading Configs from the Web
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The files in the above example could also be loaded from the web. Let's say
we've hosted, for example, the cluster templates in ``~/.starcluster/clusters``
on an http server at the url: ``http://myhost/cluster.cfg``. To load these
cluster templates from the web we just add the web address(es) to the list of
includes:

.. code-block:: ini

    [global]
    include = ~/.starcluster/keys, http://myhost/cluster.cfg, ~/.starcluster/vols

Notice in the above example we only load the cluster templates from the web. The
aws credentials, keypairs, volumes, etc. will all be loaded locally in this case.

StarCluster also supports loading the default config containing the
**[global]** section from the web::

    $ starcluster -c http://myhost/sc.cfg listvolumes

If you choose to load the default config from the web it's recommended that
only a **[global]** section is defined that includes configs either locally,
from the web, or both. It's also important

.. _tips-for-switching-regions:

Tips for Switching Regions
--------------------------
.. note::

    All examples in this section use ``us-west-1`` as the *target* region. You
    should replace ``us-west-1`` in these examples with your target region.
    Also, you do not need to pass the global ``--region`` (``-r``) flag if
    you've configured your **[aws info]** section to permanently use the target
    region.

In general, keypairs, AMIs, and EBS Volumes are all region-specific and must be
recreated or migrated before you can use them in an alternate region. To create
a new keypair in the target region, use the **createkey** command while passing
the global ``--region`` (``-r``) flag::

    $ starcluster -r us-west-1 createkey -o ~/.ssh/uswestkey.rsa myuswestkey

The above example creates a new keypair called *myuswestkey* in the
``us-west-1`` region and stores the key file in *~/.ssh/uswestkey.rsa*. Once
you've created a new keypair in the target region you must define the new
keypair in the config. For the above ``us-west-1`` example:

.. code-block:: ini

    [key myuswestkey]
    KEY_LOCATION = ~/.ssh/uswestkey.rsa

Similarly you can obtain a list of available StarCluster AMIs in the target
region using::

    $ starcluster -r us-west-1 listpublic

Finally, to (optionally) create new EBS volumes in the target region::

    $ starcluster -r us-west-1 createvolume -n myuswestvol 10 us-west-1a

Given that a *cluster template* references these region-specific items you must
either override the relevant settings at the command line using the *start*
command's option flags or create separate *cluster templates* configured for
each region you use. To override the relevant settings at the command line::

    $ starcluster -r us-west-1 start -k myuswestkey -n ami-99999999

If you often use multiple regions you will most likely want to create separate
*cluster templates* for each region by extending a common template,
*smallcluster* for example, and overriding the relevant settings:

.. code-block:: ini

    [key myuswestkey]
    KEY_LOCATION = ~/.ssh/uswestkey.rsa

    [volume myuswestvol]
    VOLUME_ID = vol-99999999
    MOUNT_PATH = /data

    [cluster uswest-cluster]
    EXTENDS = smallcluster
    KEYNAME = uswestkey
    # The AMI must live in the target region!
    NODE_IMAGE_ID = ami-9999999
    VOLUMES = myuswestvol

The above example extends the default cluster template *smallcluster* and
overrides the relevant settings needed for the target region.

With the above template defined you can use the *start* command's *-c*
(*--cluster-template*) option to use the new region-specific template to easily
create a new cluster in the target region::

    $ starcluster -r us-west-1 start -c uswest-cluster mywestcluster
