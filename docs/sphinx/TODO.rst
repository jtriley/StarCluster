StarCluster TODOs
=================
Below are the current feature requests for the StarCluster project that need
implementing:

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

Use PyStun to Restrict Cluster Acccess to User's IP-address
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
StarCluster should support restricting ssh access to the user's current
ip-address when creating a new cluster. This feature will need to use the
`pystun`_ project to correctly determine the user's public ip behind firewalls
and NAT. StarCluster's ssh* commands will also need to be modified to check
that the user's current ip has been allowed to access the cluster in the case
that they use StarCluster from multiple machines.

.. _pystun: http://pypi.python.org/pypi/pystun
