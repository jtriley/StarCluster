Using Elastic Block Storage (EBS) Volumes with StarCluster
==========================================================
StarCluster has the ability to Amazon Elastic Block Storage volumes for 
persistent storage. These volumes can be anywhere from 1GB to 1TB in size. StarCluster
will mount each volume specified in a cluster template to the *MOUNT_PATH* specified in the 
volume's configuration section on the master node. This *MOUNT_PATH* is then shared on 
all nodes using the network file system (NFS).

Using StarCluster to Create/Partition/Format a new EBS Volume (recommended)
---------------------------------------------------------------------------
StarCluster has the ability to create new EBS volumes via the **createvolume** command. 
This command completely automates the process of creating a new EBS volume, launching a *host* instance 
to attach the volume on, partitioning the volume, formatting the volume, and terminating the 
*host* instance afterwards.

Currently, the **createvolume** command only supports partitioning the *entire volume* into a single 
partition that uses all of the space on the device. The idea being that if you *really* need more than 
one partition, you're probably better off creating a new volume entirely. If this is not the case and 
you have a reasonable use-case for partitioning an EBS volume into more than one partition, please send 
a note to the StarCluster mailing list (starcluster@mit.edu).

To have StarCluster create, partition, and format a new volume for you automatically simply run:

.. code-block:: none

        $ starcluster createvolume 20 us-east-1c

The above command will create, partition, and format a new 20GB volume in the us-east-1c availability zone.
If you wish to leave the host instance used to partition/format the new volume running after creating the volume:

.. code-block:: none

        $ starcluster createvolume --no-shutdown 20 us-east-1c

This will leave the host instance running with the new volume attached. You can then login to the *host* instance 
using:

.. code-block:: none
        
        $ starcluster createvolume 20 us-east-1c

Manually Creating/Partitioning/Formatting a new EBS Volume
----------------------------------------------------------
It is recommended to use the **createvolume** command mentioned above to create new volumes for use with StarCluster. 
Below are instructions on how to manually create, partition, and format a new EBS volume using ElasticFox. These 
instructions are mostly for reference and should only be used if the **createvolume** command is not working or 
does not meet your partitioning needs.

.. toctree::
   :maxdepth: 2

   create_volume_manually.rst
