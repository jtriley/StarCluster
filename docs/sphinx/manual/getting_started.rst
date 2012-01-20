Using the Cluster
=================
After you've created a StarCluster on Amazon, it's time to login and do some
real work.  The sections below explain how to access the cluster, verify that
everything's configured properly, and how to use OpenMPI and Sun Grid Engine on
StarCluster.

For these sections we used a small two node StarCluster for demonstration. In
some cases, you may need to adjust the instructions/commands for your size
cluster. For all sections, we assume **cluster_user** is set to *sgeadmin*.  If
you've specified a different **cluster_user**, please replace sgeadmin with
your **cluster_user** in the following sections.

Logging into the master node
----------------------------
To login to the master node as root::

    $ starcluster sshmaster mycluster
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    The authenticity of host 'ec2-123-123-123-231.compute-1.amazonaws.com (123.123.123.231)' can't be established.
    RSA key fingerprint is 85:23:b0:7e:23:c8:d1:02:4f:ba:22:53:42:d5:e5:23.
    Are you sure you want to continue connecting (yes/no)? yes
    Warning: Permanently added 'ec2-123-123-123-231.compute-1.amazonaws.com,123.123.123.231' (RSA) to the list of known hosts.
    Last login: Wed May 12 00:13:51 2010 from 192.168.1.1

    The programs included with the Ubuntu system are free software;
    the exact distribution terms for each program are described in the
    individual files in /usr/share/doc/\*/copyright.

    Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
    applicable law.

    To access official Ubuntu documentation, please visit:
    http://help.ubuntu.com/

    Created From:
    Amazon EC2 Ubuntu 9.10 jaunty AMI built by Eric Hammond
    http://alestic.com http://ec2ubuntu-group.notlong.com

    StarCluster EC2 AMI created by Justin Riley (MIT)
    url: http://web.mit.edu/stardev/cluster
    email: star 'at' mit 'dot' edu
    root@master:~#

This command is used frequently in the sections below to ensure that you're
logged into the master node of a StarCluster on Amazon's EC2 as root.

Logging into a worker node
--------------------------
You also have the option of logging into any particular worker node as root by
using the **sshnode** command. First, run "starcluster listclusters" to list
the nodes::

    $ starcluster listclusters
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    ---------------------------------------------------
    mycluster (security group: @sc-mycluster)
    ---------------------------------------------------
    Launch time: 2010-02-19T20:55:20.000Z
    Zone: us-east-1c
    Keypair: gsg-keypair
    EBS volumes:
        vol-c8888888 on master:/dev/sdj (status: attached)
    Cluster nodes:
         master i-99999999 running ec2-123-123-123-121.compute-1.amazonaws.com
        node001 i-88888888 running ec2-123-123-123-122.compute-1.amazonaws.com
        node002 i-88888888 running ec2-123-23-23-24.compute-1.amazonaws.com
        node003 i-77777777 running ec2-123-23-23-25.compute-1.amazonaws.com
        ....

Then use "starcluster sshnode mycluster" to login to a node::

    $ starcluster sshnode mycluster node001
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    The authenticity of host 'ec2-123-123-123-232.compute-1.amazonaws.com (123.123.123.232)' can't be established.
    RSA key fingerprint is 86:23:b0:7e:23:c8:d1:02:4f:ba:22:53:42:d5:e5:23.
    Are you sure you want to continue connecting (yes/no)? yes
    Warning: Permanently added 'ec2-123-123-123-232.compute-1.amazonaws.com,123.123.123.232' (RSA) to the list of known hosts.
    Last login: Wed May 12 00:13:51 2010 from 192.168.1.1

    The programs included with the Ubuntu system are free software;
    the exact distribution terms for each program are described in the
    individual files in /usr/share/doc/\*/copyright.

    Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
    applicable law.

    To access official Ubuntu documentation, please visit:
    http://help.ubuntu.com/

    Created From:
    Amazon EC2 Ubuntu 9.04 jaunty AMI built by Eric Hammond
    http://alestic.com http://ec2ubuntu-group.notlong.com

    StarCluster EC2 AMI created by Justin Riley (MIT)
    url: http://web.mit.edu/stardev/cluster
    email: star 'at' mit 'dot' edu

    0 packages can be updated.
    0 updates are security updates.

    root@node001:~#

Verify /etc/hosts
-----------------
Once StarCluster is up, the /etc/hosts file should look like::

    $ starcluster sshmaster mycluster
    root@master:~# cat /etc/hosts
    # Do not remove the following line or programs that require network functionality will fail
    127.0.0.1 localhost.localdomain localhost
    10.252.167.143 master
    10.252.165.173 node001

As you can see, the head node is assigned an alias of 'master' and each node
after that is labeled node001, node002, etc.

In this example we have two nodes so only master and node001 are in /etc/hosts.

Verify Passwordless SSH
-----------------------
StarCluster should have automatically setup passwordless ssh for both root and
the CLUSTER_USER you specified.

To test this out, let's login to the master node and attempt to run the
hostname command via SSH on node001 without a password for both root and
sgeadmin (i.e. CLUSTER_USER)::

    $ starcluster sshmaster mycluster
    root@master:~# ssh node001 hostname
    node001
    root@master:~# su - sgeadmin
    sgeadmin@master:~# ssh node001 hostname
    node001
    sgeadmin@master:~# exit
    root@master:~#

Verify /home is NFS Shared
--------------------------
The /home folder on all clusters launched by StarCluster should be NFS shared
to each node. To check this, login to the master as root and run the mount
command on each node to verify that /home is mounted from the master::

    $ starcluster sshmaster mycluster
    root@master:~# ssh node001 mount
    /dev/sda1 on / type ext3 (rw)
    none on /proc type proc (rw)
    none on /sys type sysfs (rw)
    /dev/sda2 on /mnt type ext3 (rw)
    none on /proc/sys/fs/binfmt_misc type binfmt_misc (rw)
    master:/home on /home type nfs (rw,user=root,nosuid,nodev,user,addr=10.215.42.81)

The last line in the output above indicates that /home is mounted from the
master node over NFS. Running this for the rest of the nodes (e.g. node002,
node003, etc) should produce the same output.

Ensure EBS Volumes are Mounted and NFS shared (OPTIONAL)
--------------------------------------------------------
If you chose to use EBS for persistent storage (recommended) you should check
that it is mounted and shared across the cluster via NFS at the location you
specified in the config.  To do this we login to the master and run a few
commands to ensure everything is working properly.  For this example we assume
that a single 20GB volume has been attached to the cluster and that the volume
has *MOUNT_PATH=/home* in the config. If you've attached multiple EBS volumes
to the cluster, you should repeat these checks for each volume you specified in
the config.

The first thing we want to do is to make sure the device was actually attached
to the master node as a device. To check that the device is attached on the
master node, we login to the master and use "fdisk -l" to look for our volume::

    $ starcluster sshmaster mycluster

    root@master:~# fdisk -l

    ...

    Disk /dev/sdz: 21.4 GB, 21474836480 bytes
    255 heads, 63 sectors/track, 2610 cylinders
    Units = cylinders of 16065 * 512 = 8225280 bytes
    Disk identifier: 0x2a2a3cscg

    Device Boot Start End Blocks Id System
    /dev/sdz1 1 2610 20964793+ 83 Linux

From the output of fdisk above we see that there is indeed a 20GB device
/dev/sdz with partition /dev/sdz1 attached on the master node.

Next check the output of mount on the master node to ensure that the volume's
*PARTITION* setting (which defaults to 1 if not specified) has been mounted to
the volume's *MOUNT_PATH* setting specified in the config (/home for this
example)::

    root@master:~# mount
    ...
    /dev/sdz1 on /home type ext3 (rw)
    ...

From the output of mount we see that the partition /dev/sdz1 has been mounted
to /home on the master node as we specified in the config.

Finally we check that the *MOUNT_PATH* specified in the config for this volume
has been NFS shared to each cluster node by running mount on each node and
examining the output::

    $ starcluster sshmaster mycluster
    root@master:~# ssh node001 mount
    /dev/sda1 on / type ext3 (rw)
    none on /proc type proc (rw)
    none on /sys type sysfs (rw)
    /dev/sda2 on /mnt type ext3 (rw)
    none on /proc/sys/fs/binfmt_misc type binfmt_misc (rw)
    master:/home on /home type nfs (rw,user=root,nosuid,nodev,user,addr=10.215.42.81)
    root@master:~# ssh node002 mount
    ...
    master:/home on /home type nfs (rw,user=root,nosuid,nodev,user,addr=10.215.42.81)
    ...

The last line in the output above indicates that *MOUNT_PATH* (/home for this
example) is mounted on each worker node from the master node via NFS.  Running
this for the rest of the nodes (e.g. node002, node003, etc) should produce the
same output.

Verify scratch space
--------------------
Each node should be set up with approximately 140GB or more of local scratch
space for writing temporary files instead of storing temporary files on NFS.
The location of the scratch space is /scratch/CLUSTER_USER. So, for this
example the local scratch for CLUSTER_USER=sgeadmin is /scratch/sgeadmin.

To verify this, login to the master and run "ls -l /scratch"::

    $ starcluster sshmaster mycluster
    root@master:/# ls -l /scratch/
    total 0
    lrwxrwxrwx 1 root root 13 2009-09-09 14:34 sgeadmin -> /mnt/sgeadmin

From the output above we see that /scratch/sgeadmin has been symbolically
linked to /mnt/sgeadmin

Next we run the df command to verify that at least ~140GB is available on /mnt
(and thus /mnt/sgeadmin)::

    root@master:~# df -h
    Filesystem Size Used Avail Use% Mounted on
    ...
    /dev/sda2 147G 188M 140G 1% /mnt
    ...
    root@master:~#

Compile and run a "Hello World" OpenMPI program
-------------------------------------------------
Below is a simple Hello World program in MPI

.. code-block:: c

    #include <stdio.h> /* printf and BUFSIZ defined there */
    #include <stdlib.h> /* exit defined there */
    #include <mpi.h> /* all MPI-2 functions defined there */

    int main(argc, argv)
            int argc;
            char *argv[];
            {
            int rank, size, length;
            char name[BUFSIZ];

            MPI_Init(&argc, &argv);
            MPI_Comm_rank(MPI_COMM_WORLD, &rank);
            MPI_Comm_size(MPI_COMM_WORLD, &size);
            MPI_Get_processor_name(name, &length);

            printf("%s: hello world from process %d of %d\n", name, rank, size);

            MPI_Finalize();

            exit(0);
    }

Save this code to a file called helloworldmpi.c in /home/sgeadmin. You can then
compile and run the code across the cluster like so::

    $ starcluster sshmaster mycluster
    root@master:~# su - sgeadmin
    sgeadmin@master:~$ mpicc helloworldmpi.c -o helloworldmpi
    sgeadmin@master:~$ mpirun -n 2 -host master,node001 ./helloworldmpi
    master: hello world from process 0 of 2
    node001: hello world from process 1 of 2
    sgeadmin@master:~$

Obviously if you have more nodes, the -host mater,node001 list specified will
need to be extended. You can also create a hostfile instead of listing each
node for OpenMPI to use that looks like::

    sgeadmin@:~$ cat /home/sgeadmin/hostfile
    master
    node001

After creating this hostfile, you can now call mpirun with less options::

    sgeadmin@master:~$ mpirun -n 2 -hostfile /home/sgeadmin/hostfile ./helloworldmpi
    master: hello world from process 0 of 2
    node001: hello world from process 1 of 2
    sgeadmin@master:~$
