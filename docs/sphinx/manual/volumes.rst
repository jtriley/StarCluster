Using EBS Volumes for Persistent Storage
========================================
StarCluster utilizes Amazon's Elastic Block Storage (EBS) volumes for
persistent storage. These volumes can be anywhere from 1GB to 1TB in size.
StarCluster will mount each volume specified in a cluster template to the
**MOUNT_PATH** specified in the volume's configuration section on the master
node. This **MOUNT_PATH** is then shared on all nodes using the network file
system (NFS).

For example, suppose we have the following (abbreviated) configuration defined:

.. code-block:: ini

        [vol myvol]
        volume_id = vol-v99999
        mount_path = /data

        [cluster smallcluster]
        cluster_size=3
        keyname=mykey
        node_instance_type=m1.small
        node_image_id=ami-8cf913e5
        volumes=myvol

In this case, whenever a cluster is launched using the *smallcluster* template
StarCluster will attach the EBS volume *vol-v99999* to the *master* node on
*/data* and then NFS-share */data* to all the nodes in the cluster.

Create, Partition, and Format a new EBS Volume
----------------------------------------------
StarCluster's **createvolume** command completely automates the process of
creating a new EBS volume, launching a *host* instance to attach the volume to,
partitioning the volume, and formatting the volume.

.. warning::

        The **createvolume** command only supports partitioning the *entire
        volume* into a single partition that uses all of the space on the
        device. If you *really* need more than one partition you're probably
        better off creating a new volume entirely.  If this is not the case and
        you have a use-case for partitioning an EBS volume into more than one
        partition, please send a note to the StarCluster mailing list
        (starcluster 'at' mit 'dot' edu).

To have StarCluster create, partition, and format a new volume for you
automatically simply run: ::

        $ starcluster createvolume 20 us-east-1c

This command will launch a host instance in the us-east-1c availability zone,
create a 20GB volume in us-east-1c, attach the new volume to the host instance,
and format the entire volume.

You can also use the --bid option to request a spot instance when creating the
volume host: ::

        $ starcluster createvolume 20 us-east-1c --bid 0.50

.. warning::

        In previous versions the **createvolume** command used to terminate the
        host instance after creating the volume, however, the latest version
        **does not do this by default** in order to allow multiple volumes to
        be created in the same zone with a *single* host instance. You can pass
        the *--shutdown-volume-host* option to the *createvolume* command to
        have StarCluster automatically shutdown the volume host after creating
        the new volume.

Let's look at an example::

        $ starcluster createvolume 20 us-east-1c
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

Notice the warning at the bottom of the above output. StarCluster will leave
the host instance running with the new volume attached after creating and
formatting the new volume. This allows multiple volumes to be created in a
given availability zone without launching a new instance for each volume. To
see the volume hosts simply run the *listclusters* command: ::

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

From the above example we see that we have a volume-host in us-east-1c called
*volhost-us-east-1c*. Any volumes that were created will still be attached to the
volume host until you terminate the *volumecreator* cluster. If you'd rather
detach the volume after it's been successfully created use the
*--detach-volume* (-d) option: ::

        $ starcluster createvolume --detach-volume 20 us-east-1c

You can login to a volume host instance using: ::

        $ starcluster sshnode volumecreator volhost-us-east-1c

After logging in you can inspect the volume, upload data, etc.  When you're
done using the volumecreator cluster don't forget to terminate it::

        $ starcluster terminate volumecreator

If you'd rather avoid having to terminate the volumecreator each time you can
pass the *--shutdown-volume-host (-s)* option to the *createvolume* command to
have StarCluster automatically terminate the host-instance after successfully
creating the new volume: ::

        $ starcluster createvolume --shutdown-volume-host 20 us-east-1c
