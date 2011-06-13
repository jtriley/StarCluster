Using EBS Volumes for Persistent Storage
========================================
StarCluster utilizes Amazon's Elastic Block Storage (EBS) volumes for
persistent storage. These volumes can be anywhere from 1GB to 1TB in size.
StarCluster will mount each volume specified in a cluster template to the
**MOUNT_PATH** specified in the volume's configuration section on the master
node. This **MOUNT_PATH** is then shared on all nodes using the network file
system (NFS).

Create, Partition, and Format a new EBS Volume
----------------------------------------------
StarCluster's **createvolume** command completely automates the process of
creating a new EBS volume, launching a *host* instance to attach the volume on,
partitioning the volume, formatting the volume, and terminating the *host*
instance afterwards.

.. warning::

        The **createvolume** command only supports partitioning the *entire
        volume* into a single partition that uses all of the space on the
        device. If you *really* need more than one partition you're probably
        better off creating a new volume entirely.  If this is not the case and
        you have a use-case for partitioning an EBS volume into more than one
        partition, please send a note to the StarCluster mailing list
        (starcluster 'at' mit 'dot' edu).

To have StarCluster create, partition, and format a new volume for you
automatically simply run:

.. code-block:: none

        $ starcluster createvolume 20 us-east-1c

The above command will create, partition, and format a new 20GB volume in the
us-east-1c availability zone.  If you wish to leave the host instance used to
partition/format the new volume running after creating the volume:

.. code-block:: none

        $ starcluster createvolume --no-shutdown 20 us-east-1c

This will leave the host instance running with the new volume attached. You can
then login to the *host* instance using:

.. code-block:: none

        $ starcluster createvolume 20 us-east-1c
