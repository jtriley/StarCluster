StarCluster TODOs
=================
Below are the current feature requests for the StarCluster project that need
implementing:

Config Includes
^^^^^^^^^^^^^^^
Allow including multiple files in the StarCluster config file. This would allow
users to separate their *private* credentials from their cluster templates.
This is really useful if you want to, say, share a common config between
members of a group. Each member would have their credentials stored in a
separate credentials file, say *$HOME/.starcluster/creds*, and could then
easily pull in the latest config updates from the web, git, etc. For example::

        [include ~/.starcluster/creds]

This line would pull in any config sections defined in *$HOME/.starcluster/creds*.
Here's an example *creds* file::

        [aws info]
        aws_access_key_id = #your aws access key id
        aws_secret_access_key = #your aws secret access key
        aws_user_id = #your aws user id

The main config file, *$HOME/.starcluster/config*, would then include this file
to pick up the credentials::

        [global]
        default_template = smallcluster

        [include ~/.starcluster/creds]

        [cluster smallcluster]
        cluster_size = 4
        keypair = mykey
        node_instance_type = m1.large
        node_image_id = ami-0af31963

As you can see this removes the private sections from the main StarCluster
config file which in turn makes the main config file much easier to share.

Add 'put' and 'get' Commands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
These commands should provide the same functionality as the *scp* command from
OpenSSH and should be easier to use with StarCluster instances. Below are a
couple example usage scenarios.

.. note::
        All of the examples below should automatically handle recursion without
        requiring an extra command line flag.

Copy a file or dir to the master as root
########################################
::

        $ starcluster put mycluster /path/to/file/or/dir /path/on/remote/server

Copy a file or dir to the master as normal user
###############################################
::

        $ starcluster put mycluster --user myuser /local/path /remote/path

Copy a file or dir to a node (node001 in this example)
######################################################
::

        $ starcluster put mycluster --node node001 /local/path /remote/path


Support for Amazon VPC
^^^^^^^^^^^^^^^^^^^^^^
Add the ability to configure StarCluster to launch the cluster instances inside
of an `Amazon VPC`_. Should just involve adding a *SubnetId* parameter to the
`run_instances`_ boto call. `Feature requested by Adam Kraut`_.


.. _Feature requested by Adam Kraut: http://mailman.mit.edu/pipermail/starcluster/2011-April/000706.html

.. _Amazon VPC: http://aws.amazon.com/vpc
.. _run_instances: http://boto.s3.amazonaws.com/ref/ec2.html#boto.ec2.connection.EC2Connection.run_instances

Improved Eucalyptus Support
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Need to subclass starcluster.cluster.Cluster and starcluster.awsutils.EasyEC2
for Eucalyptus to handle the lack of the following API features in ECC:

  * `DescribeInstanceAttribute`_
  * `Tags API`_
  * `Filters API`_

.. _Tags API: http://docs.amazonwebservices.com/AWSEC2/latest/APIReference/index.html?ApiReference-query-CreateTags.html
.. _DescribeInstanceAttribute: http://docs.amazonwebservices.com/AWSEC2/latest/APIReference/index.html?ApiReference-query-DescribeInstanceAttribute.html
.. _Filters API: http://aws.amazon.com/releasenotes/Amazon-EC2/4174

Add More Options to "addnode" command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The following options need to be added to the addnode command:

  * --image-id (-i)
  * --instance-type (-I)
  * --availability-zone (-z)
  * --bid (-b)

Dan Yamins has a `pull request`_ for this that needs to be merged.

Add Support for Load Balancing a Given SGE Queue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Load balancer should support balancing Sun Grid Engine queues other than just
all.q. This is useful if you want to load balance many different queues with
varying configurations. In this case you can launch a separate load-balancer
process for each queue.

Dan Yamins has a `pull request`_ for this that needs to be merged.

.. _pull request: https://github.com/jtriley/StarCluster/pull/20

Add HTTP Proxy Settings for Boto to StarCluster Config
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It looks like boto supports using an HTTP proxy:
http://code.google.com/p/boto/wiki/BotoConfig

Need to add a *[proxy]* section to the starcluster config that gets passed on
to the boto connection.
