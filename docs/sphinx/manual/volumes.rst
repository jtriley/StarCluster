########################################
Using EBS Volumes for Persistent Storage
########################################
StarCluster supports using Amazon's Elastic Block Storage (EBS) volumes for
persistent storage. These volumes can be anywhere from 1GB to 1TB in size.
StarCluster will attach each volume specified in a cluster template to the
master node and then share the volume(s) to the rest of the nodes in the
cluster via the network file system (NFS). Each volume will be mounted to the
path specified by the ``MOUNT_PATH`` setting in the volume's configuration
section.

For example, suppose we have the following configuration defined:

.. code-block:: ini

    [vol myvol]
    volume_id = vol-v9999999
    mount_path = /data

    [cluster smallcluster]
    cluster_size=3
    keyname=mykey
    node_instance_type=m1.small
    node_image_id=ami-8cf913e5
    volumes=myvol

In this case, whenever a cluster is launched using the ``smallcluster`` template
StarCluster will attach the EBS volume ``vol-v9999999`` to the ``master`` node on
``/data`` and then NFS-share ``/data`` to all the nodes in the cluster.

It's also possible to use multiple EBS volumes by specifying a list of volumes
in a cluster template:

.. note::
    Each volume specified in a cluster template *must* have a unique
    ``MOUNT_PATH`` otherwise an error will be raised.

.. code-block:: ini

    [vol cancerdata]
    volume_id = vol-v8888888
    mount_path = /data/cancer

    [vol genomedata]
    volume_id = vol-v9999999
    mount_path = /data/genome

    [cluster smallcluster]
    cluster_size=3
    keyname=mykey
    node_instance_type=m1.small
    node_image_id=ami-8cf913e5
    volumes=cancerdata, genomedata

.. _create-and-format-ebs-volumes:

**********************************
Create and Format a new EBS Volume
**********************************
StarCluster's **createvolume** command completely automates the process of
creating a new EBS volume. This includes launching a host instance in the
target zone, attaching the new volume to the host, and formatting the entire
volume.

.. note::

    The **createvolume** command simply formats the *entire volume* using all
    of the space on the device rather than creating partitions. This makes it
    easier to resize the volume and expand the filesystem later on if you run
    out of disk space.

To create and format a new volume simply specify a volume size in GB and the
availability zone to create the volume in::

    $ starcluster createvolume --name=my-data 20 us-east-1c

.. _AWS web console: http://aws.amazon.com/console

The above command will launch a host instance in the us-east-1c availability
zone, create a 20GB volume in us-east-1c, attach the new volume to the host
instance, and format the entire volume. The ``--name`` option allows you name
the volume for easy reference later on when using the **listvolumes** command
or the `AWS web console`_.

If you wish to apply an arbitrary tag to the new volume use the ``--tag``
option::

    $ starcluster createvolume --tag=mytag 20 us-east-1c

If you want to create a key/value tag::

    $ starcluster createvolume --tag mytag=myvalue 20 us-east-1c

You can also use the ``--bid`` option to request a spot instance when creating
the volume host::

    $ starcluster createvolume 20 us-east-1c --bid 0.50

.. warning::

    StarCluster does not terminate the host instance after creating a volume.
    This allows multiple volumes to be created in the same zone using a
    *single* host instance. You can pass the ``--shutdown-volume-host`` option
    to the **createvolume** command to if you'd rather automatically shutdown
    the volume host after creating the new volume.

Let's look at an example of creating a 20GB volume in ``us-east-1c``::

    $ starcluster createvolume --name=myvol --bid=0.50 20 us-east-1c
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> No keypair specified, picking one from config...
    >>> Using keypair: jtriley
    >>> Creating security group @sc-volumecreator...
    >>> No instance in group @sc-volumecreator for zone us-east-1c,
    >>> launching one now.
    >>> Waiting for volume host to come up... (updating every 30s)
    >>> Waiting for open spot requests to become active...
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Waiting for all nodes to be in a 'running' state...
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Waiting for SSH to come up on all nodes...
    1/1 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| 100%
    >>> Checking for required remote commands...
    >>> Creating 1GB volume in zone us-east-1c
    >>> New volume id: vol-2f3a5344
    >>> Waiting for new volume to become 'available'...
    >>> Attaching volume vol-2f3a5344 to instance i-fb9ceb95...
    >>> Formatting volume...
    mke2fs 1.41.11 (14-Mar-2010)
    Filesystem label=
    OS type: Linux
    Block size=4096 (log=2)
    Fragment size=4096 (log=2)
    Stride=0 blocks, Stripe width=0 blocks
    65536 inodes, 262144 blocks
    13107 blocks (5.00%) reserved for the super user
    First data block=0
    Maximum filesystem blocks=268435456
    8 block groups
    32768 blocks per group, 32768 fragments per group
    8192 inodes per group
    Superblock backups stored on blocks:
            32768, 98304, 163840, 229376

    Writing inode tables: done
    Creating journal (8192 blocks): done
    Writing superblocks and filesystem accounting information: done

    This filesystem will be automatically checked every 30 mounts or
    180 days, whichever comes first.  Use tune2fs -c or -i to override.
    >>> Leaving volume vol-2f3a5344 attached to instance i-fb9ceb95
    >>> Not terminating host instance i-fb9ceb95
    *** WARNING - There are still volume hosts running: i-fb9ceb95
    *** WARNING - Run 'starcluster terminate volumecreator' to terminate
    *** WARNING - *all* volume host instances once they're no longer needed
    >>> Creating volume took 7.396 mins
    >>> Your new 1GB volume vol-2f3a5344 has been created successfully

In the above example we name the volume ``myvol`` and use a spot instance for
the volume host. Notice the warning at the bottom of the above output.
StarCluster will leave the host instance running with the new volume attached
after creating and formatting the new volume. This allows multiple volumes to
be created in a given availability zone without launching a new instance for
each volume. To see the volume hosts simply run the **listclusters** command::

    $ starcluster listclusters volumecreator
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    -------------------------------------------------
    volumecreator (security group: @sc-volumecreator)
    -------------------------------------------------
    Launch time: 2011-06-13 13:51:25
    Uptime: 00:02:09
    Zone: us-east-1c
    Keypair: mykey
    EBS volumes: N/A
    Cluster nodes:
        volhost-us-east-1c running i-fd9clb9z  (spot sir-2a8zb4lr)
    Total nodes: 1

From the above example we see that we have a volume-host in ``us-east-1c``
called ``volhost-us-east-1c``. Any volumes that were created will still be
attached to the volume host until you terminate the ``volumecreator`` cluster.
If you'd rather detach the volume after it's been successfully created use the
``--detach-volume`` (``-d``) option::

    $ starcluster createvolume --detach-volume 20 us-east-1c

You can login to a volume host instance using::

    $ starcluster sshnode volumecreator volhost-us-east-1c

After logging in you can inspect the volume, upload data, etc.  When you're
done using the volumecreator cluster don't forget to terminate it::

    $ starcluster terminate volumecreator

If you'd rather avoid having to terminate the volumecreator each time you can
pass the ``--shutdown-volume-host`` (``-s``) option to the **createvolume**
command to have StarCluster automatically terminate the host-instance after
successfully creating the new volume::

    $ starcluster createvolume --shutdown-volume-host 20 us-east-1c

.. _managing-ebs-volumes:

*************************************
Managing EBS Volumes with StarCluster
*************************************
In addition to creating and formatting new EBS volumes StarCluster also allows
you to browse and remove your EBS volumes.

Getting Volume Status
=====================
To get a list of all your volumes as well as their current status use the
**listvolumes** command::

    $ starcluster listvolumes
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    volume_id: vol-be279s08
    size: 5GB
    status: available
    availability_zone: us-east-1d
    create_time: 2011-10-22 16:18:57

    Total: 1

To list details for a single volume by name use the ``--name`` (``-n``)
option::

    $ starcluster listvolumes --name my-big-data

To list details for a single volume by id use the ``--volume-id``
(``-v``)::

    $ starcluster listvolumes -v vol-99999999

If you'd like to see details for all volumes with a given tag use the ``--tag``
(``-t``) option::

    $ starcluster listvolumes -t my-big-data
    $ starcluster listvolumes -t mytag=myvalue

You can also filter the volumes by status using the ``--status`` (``-S``)
flag::

    $ starcluster listvolumes -S available

and by volume size (in GB) using the ``--size`` (``-s``) option::

    $ starcluster listvolumes -s 20

and also by attachment state using the ``--attach-status`` (``-a``) option::

    $ starcluster listvolumes -a attached

Other filters are available, have a look at the help menu for more details::

    $ starcluster listvolumes --help

Removing Volumes
================
.. warning:: This process cannot be reversed!

To **permanently** remove an EBS volume use the **removevolume** command::

    $ starcluster removevolume vol-99999999

Resizing Volumes
================
After you've created and used an EBS volume over time you may find that you
need to add additional disk space to the EBS volume. Normally you would need to
snapshot the volume, create a new, larger, volume from the snapshot, attach the
new volume to an instance, and expand the filesystem to fit the new volume.
Fortunately, StarCluster's **resizevolume** command streamlines this process
for you.

.. note::

     The EBS volume must either be unpartitioned or contain only a single
     partition. Any other configuration will be aborted.

For example, to resize a 10GB volume, say ``vol-99999999``, to 20GB::

    $ starcluster resizevolume vol-99999999 20

The above command will create a *new*, larger, 20GB volume containing the data
from the original volume vol-99999999. The new volume's filesystem will also be
expanded to fit the new volume size.

Just like the **createvolume** command, the **resizevolume** command will also
launch a host instance in order to attach the new volume and expand the
volume's filesystem. Similarly, if you wish to shutdown the host instance
automatically after the new resized volume has been created, use the
``--shutdown-volume-host`` option::

    $ starcluster resizevolume --shutdown-volume-host vol-99999999 20

Otherwise, you will need to terminate the volume host manually after the
**resizevolume** command completes.

Moving Volumes Across Availability Zones
========================================
In some cases you may need to replicate a given volume to another availability
zone so that the data can be used with instances in a different data center.
The **resizevolume** command supports creating a newly expanded volume within
an alternate availability zone via the ``--zone`` (``-z``), flag::

    $ starcluster resizevolume -z us-east-1d vol-9999999 20

The above command will create a new 20GB volume in ``us-east-1d`` containing
the data in ``vol-99999999``. If you only want to move the volume data without
resizing simply specify the same size as the original volume.
