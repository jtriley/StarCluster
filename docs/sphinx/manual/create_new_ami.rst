###############################
Customizing the StarCluster AMI
###############################
The StarCluster base AMIs are meant to be fairly minimal in terms of the
software installed. If you'd like to customize the software installed on the
AMI you can create a new AMI based on the StarCluster AMIs using the
**s3image** and **ebsimage** commands.

***************************************
Launching and Customizing an Image Host
***************************************
In order to create a new AMI you must first launch an instance of an existing
AMI that you wish to extend. This instance is referred to as an *image host*
and is used to build a new AMI. The *image host* allows you to easily customize
the software environment included in your new AMI simply by logging into the
*image host* and making the necessary changes.

Launching a New Image Host
==========================
When launching a new *image host* it is recommended that you start a new
cluster called *imagehost* using the following command::

    $ starcluster start -o -s 1 -i <INSTANCE-TYPE> -n <BASE-AMI-ID> imagehost

.. note::

    Replace **<INSTANCE-TYPE>** with an instance type that is compatible with
    your **<BASE-AMI-ID>**. If you're not creating a new Cluster/GPU Compute
    AMI, you can use m1.small (32bit) or m1.large (64bit) to minimize costs
    when creating the image. If you *are* creating a new Cluster/GPU Compute
    AMI the you'll need to launch the *image host* with a Cluster/GPU Compute
    instance type.

This command will create a single node (``-s 1``) cluster called *imagehost*
using the AMI you wish to customize (``-n <BASE-AMI-ID>``) and a compatible
instance type (``-i <INSTANCE-TYPE>``). The ``-o`` option tells StarCluster to
only create the instance(s) and not to setup and configure the instance(s) as a
cluster.  This way you start with a *clean* version of the AMI you're
extending.

You can also use a spot instance as the image host by passing ``--bid``
(``-b``) option::

    $ starcluster start -o -s 1 -b 0.50 -i <INSTANCE-TYPE> -n <BASE-AMI-ID> imagehost

If you used the ``-o`` option you'll need to periodically run the
**listclusters** command to check whether or not the  *image host* is up::

    $ starcluster listclusters --show-ssh-status imagehost

Once the *image host* is up, login and customize the instance's software
environment to your liking::

    $ starcluster sshmaster imagehost

The above command will log you in as *root* at which point you can install new
software using either *apt-get* or by manually installing the software from
source. Once you've customized the *image host* to your liking you're ready to
create a new AMI.

Using an Existing Instance as an Image Host
===========================================
Of course you don't *have* to use the above method for creating a new AMI. You
can use *any* instance on EC2 as an *image host*. The *image host* also doesn't
have to be started with StarCluster. The only requirement is that you must have
the keypair that was used to launch the instance defined in your StarCluster
configuration file.

.. note::

    In previous versions it was strongly recommended *not* to use nodes
    launched by StarCluster as *image hosts*. This is no longer the case and
    you can now use any node/instance started by StarCluster as an image host.

*************************************
Creating a New AMI from an Image Host
*************************************
After you've finished customizing the software environment on the *image host*
you're ready to create a new AMI. Before creating the image you must decide
whether to create an *instance-store* (aka *S3-backed*) AMI or an EBS-backed
AMI. Below are some of the advantages and disadvantages of using S3 vs EBS:

+--------------------------------+------------------------------------------------------------------------------------------------------------------+-----------------------------------+
| Factor                         | EBS backed AMI's                                                                                                 | S3 backed AMI's                   |
+================================+==================================================================================================================+===================================+
| Root Storage Size              | 1TB                                                                                                              | 10GB                              |
+--------------------------------+------------------------------------------------------------------------------------------------------------------+-----------------------------------+
| Instances can be Stopped       | Yes                                                                                                              | No                                |
+--------------------------------+------------------------------------------------------------------------------------------------------------------+-----------------------------------+
| Boot Time                      | Faster (~1min)                                                                                                   | Slower (~5mins)                   |
+--------------------------------+------------------------------------------------------------------------------------------------------------------+-----------------------------------+
| Data Persistence               | EBS volume attached as root disk (persist)                                                                       | Local root disk (doesn't persist) |
+--------------------------------+------------------------------------------------------------------------------------------------------------------+-----------------------------------+
| Charges                        | Volume Storage + Volume Usage + AMI Storage + Instance usage                                                     | AMI Storage + Instance usage      |
+--------------------------------+------------------------------------------------------------------------------------------------------------------+-----------------------------------+
| Customized AMI Storage Charges | Lower (charged only for the changes)                                                                             | Higher (full storage charge)      |
+--------------------------------+------------------------------------------------------------------------------------------------------------------+-----------------------------------+
| Instance Usage Charge          | No charge for stopped instances. Charged full instance hour for *every* transition from stopped to running state | Not Applicable                    |
+--------------------------------+------------------------------------------------------------------------------------------------------------------+-----------------------------------+

(see `Amazon's summary of EBS vs S3 backed AMIs`_ for more details)

If you're in doubt about which type of AMI to create, choose an EBS-backed AMI.
This will allow you to create clusters that you can start and stop repeatedly
without losing data on the root disks in between launches. Using EBS-backed
AMIs also allows you to snapshot the root volume of an instance for back-up
purposes and to easily expand the root disk size of the AMI without paying full
storage charges. In addition, EBS-backed AMIs usually have much faster start up
time given that there's no transferring of image files from S3 as is the case
with S3-backed AMIs.

Creating an EBS-Backed AMI
==========================
This section assumes you want to create an *EBS-backed* AMI. See the next
section if you'd prefer to create an S3-backed AMI instead. To create a new
EBS-backed AMI, use the **ebsimage** command::

    $ starcluster ebsimage i-9999999 my-new-image

In the above example, *i-99999999* is the instance id of the instance you wish
to create a new image from. If the instance is a part of a cluster, such as
*imagehost* in the sections above, you can get the instance id from the output
of the **listclusters** command. Otherwise, you can get the instance id of
*any* node, launched by StarCluster or not, via the **listinstances** command.
The argument after the instance id is the name you wish to give to your new
AMI.

After the **ebsimage** command completes successfully it will print out the new
AMI id that you then can use in the *node_image_id*/*master_image_id* settings
in your *cluster templates*.

Creating an S3-backed (instance-store) AMI
==========================================
This section assumes you want to create an *S3-backed* AMI. See the previous
section if you'd prefer to create an EBS AMI instead. To create a new S3-backed
AMI, use the **s3image** command::

    $ starcluster s3image i-9999999 my-new-image mybucket

In the above example, *i-99999999* is the instance id of the instance you wish
to create a new image from. If the instance is a part of a cluster, such as
*imagehost* in the sections above, you can get the instance id from the output
of the **listclusters** command. The arguments after the instance id are the
name you wish to give the AMI and the name of a bucket in S3 to store the new
AMI's files in. The bucket will be created if it doesn't exist.

After the **s3image** command completes successfully it will print out the new
AMI id that you can then use in the *node_image_id*/*master_image_id* settings
in your *cluster templates*.

.. _report an issue on github: https://github.com/jtriley/StarCluster/issues
.. _Amazon's summary of EBS vs S3 backed AMIs: http://docs.amazonwebservices.com/AWSEC2/latest/UserGuide/index.html?Concepts_BootFromEBS.html#summary_differences_ebs_s3
