Getting Started with StarCluster
================================
After you've created a StarCluster on Amazon, it's time to login and do some real work. 
The sections below explain how to access the cluster, verify that everything's configured 
properly, and how to use OpenMPI and Sun Grid Engine on StarCluster. 

For these sections we used a small two node StarCluster for demonstration. In some cases, you 
may need to adjust the instructions/commands for your size cluster. For all sections, we assume 
**cluster_user** is set to *sgeadmin*.  If you've specified a different **cluster_user**, please 
replace sgeadmin with your **cluster_user** in the following sections.

Logging into the master node
----------------------------
To login to the master node as root:

.. code-block:: none 

        $ starcluster sshmaster

        StarCluster - (http://web.mit.edu/starcluster)
        Author: justin.t.riley 'at' gmail 'dot' com
        Please submit bug reports to starcluster 'at' mit 'dot' edu

        >>> MASTER NODE: ec2-174-129-113-176.compute-1.amazonaws.com
        The authenticity of host 'ec2-174-129-113-176.compute-1.amazonaws.com (174.129.113.176)' can't be established.
        RSA key fingerprint is 27:32:cf:df:f0:c8:01:dd:ef:za:02:c3:c4:5s:5f:4b.
        Are you sure you want to continue connecting (yes/no)? yes
        Warning: Permanently added 'ec2-174-129-113-176.compute-1.amazonaws.com,174.129.113.176' (RSA) to the list of known hosts.
        Linux domU-12-31-38-00-A0-61 2.6.21.7-2.fc8xen #1 SMP Fri Feb 15 12:39:36 EST 2008 i686

        The programs included with the Ubuntu system are free software;
        the exact distribution terms for each program are described in the
        individual files in /usr/share/doc/*/copyright.

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
        root@domU-12-31-38-00-A0-61:~#

This command is used frequently in the sections below to ensure that you're logged into 
the master node of a StarCluster on Amazon's EC2 as root.

Logging into a worker node
--------------------------
You also have the option of logging into any particular worker node as root by using the 
-n option to StarCluster. First, run starcluster listclusters to list the nodes:

.. code-block:: none

        $ starcluster listclusters 
        StarCluster - (http://web.mit.edu/starcluster)
        Author: justin.t.riley 'at' gmail 'dot' com
        Please submit bug reports to starcluster 'at' mit 'dot' edu

        >>> EC2 Instances:
        [0] ec2-174-129-113-176.compute-1.amazonaws.com running (ami-8f9e71e6)
        [1] ec2-75-101-202-225.compute-1.amazonaws.com running (ami-8f9e71e6)

Then use the -n option to login to a particular node

.. code-block:: none

        $ starcluster -n 1

        StarCluster - (http://web.mit.edu/starcluster)
        Author: justin.t.riley 'at' gmail 'dot' com
        Please submit bug reports to starcluster 'at' mit 'dot' edu

        >>> Logging into node: ec2-75-101-202-225.compute-1.amazonaws.com
        The authenticity of host 'ec2-75-101-202-225.compute-1.amazonaws.com (75.101.202.225)' can't be established.
        RSA key fingerprint is 27:32:cf:df:f0:c8:01:dd:ef:za:02:c3:c4:5s:5f:4b.
        Are you sure you want to continue connecting (yes/no)? yes
        Warning: Permanently added 'ec2-75-101-202-225.compute-1.amazonaws.com,75.101.202.225' (RSA) to the list of known hosts.
        Linux domU-12-31-38-00-A2-43 2.6.21.7-2.fc8xen #1 SMP Fri Feb 15 12:39:36 EST 2008 i686

        The programs included with the Ubuntu system are free software;
        the exact distribution terms for each program are described in the
        individual files in /usr/share/doc/*/copyright.

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

        root@domU-12-31-38-00-A2-43:~#

Verify /etc/hosts
-----------------
Once StarCluster is up, the /etc/hosts file should look like:

.. code-block:: none

        $ starcluster -m
        root@domU-12-31-38-00-A2-43:~# cat /etc/hosts
        # Do not remove the following line or programs that require network functionality will fail
        127.0.0.1 localhost.localdomain localhost
        10.252.167.143 domU-12-31-38-00-A0-61.compute-1.internal domU-12-31-38-00-A0-61 master
        10.252.165.173 domU-12-31-38-00-A2-43.compute-1.internal domU-12-31-38-00-A2-43 node001

As you can see, the head node is assigned an alias of 'master' and each node after that is labeled node001, node002, etc.

In this example we have two nodes so only master and node001 are in /etc/hosts

Verify Passwordless SSH
-----------------------
StarCluster should have automatically setup passwordless ssh for both root and the CLUSTER_USER you specified.

To test this out, let's login to the master node and attempt to run the hostname command via SSH on node001 without a password for both root and sgeadmin (ie CLUSTER_USER):

.. code-block:: none

        $ starcluster -m
        root@domU-12-31-38-00-A0-61:~# ssh node001 hostname
        domU-12-31-38-00-A2-43
        root@domU-12-31-38-00-A0-61:~# su - sgeadmin
        sgeadmin@domU-12-31-38-00-A0-61:~# ssh node001 hostname
        domU-12-31-38-00-A2-43
        sgeadmin@domU-12-31-38-00-A0-61:~# exit
        root@domU-12-31-38-00-A0-61:~#

Ensure EBS is mounted to /home (OPTIONAL)
-----------------------------------------
If you chose to use EBS for persistent storage (recommended) you should check that it is 
mounted on /home and shared across the cluster via NFS. To do this we login to the master 
and run a few commands to ensure everything is working properly.

The first thing we want to do is to make sure the device was actually attached to the master 
node on the device specified by VOLUME_DEVICE/VOLUME_PARTITION in your configuration file. 
For this example VOLUME_DEVICE=?/dev/sdj? and VOLUME_PARTITION=?/dev/sdj1?.

.. code-block:: none

        $ starcluster -m

        root@domU-12-31-38-00-A0-61:~# fdisk -l

        ...

        Disk /dev/sdj: 21.4 GB, 21474836480 bytes
        255 heads, 63 sectors/track, 2610 cylinders
            Units = cylinders of 16065 * 512 = 8225280 bytes
            Disk identifier: 0x2a2a3cscg

            Device Boot Start End Blocks Id System
            /dev/sdj1 1 2610 20964793+ 83 Linux


From the output of fdisk above we see that there is indeed a device /dev/sdj with 
partition /dev/sdj1 attached on the master node.

Next check the output of mount on the master node to ensure the VOLUME_PARTITION 
has been mounted to /home:

.. code-block:: none

        root@domU-12-31-38-00-A0-61:~# mount
        ...
        /dev/sdj1 on /home type ext3 (rw)
        ...

From the output of mount we see that the partition /dev/sdj1 has been mounted to /home 
on the master node.

Next we check that our home folders that are stored in the EBS volume show up in /home 
on the master node:

.. code-block:: none

        root@domU-12-31-38-00-A0-61:~# cd /home
        root@domU-12-31-38-00-A0-61:/home# ls
        lost+found sgeadmin

Here we see that sgeadmin's home folder is indeed on the cluster. This means that the next 
time we launch a new StarCluster using this EBS volume all of the data/configuration in 
/home/sgeadmin will be automatically restored.

Verify /home is NFS Shared
--------------------------
The last thing to check is that /home has been nfs shared across the cluster.

To verify we create a test file called 'testfile' on the master node in /home/sgeadmin 
and verify that it also shows up in each node's /home/sgeadmin folder.

.. code-block:: none

        $ starcluster -m
        root@domU-12-31-38-00-A0-61:~# su - sgeadmin
        sgeadmin@domU-12-31-38-00-A0-61:~# touch testfile
        sgeadmin@domU-12-31-38-00-A0-61:~# ssh node001 ls -l ~/testfile
        -rw-r--r-- 1 sgeadmin sgeadmin 0 2009-09-09 15:48 /home/jtriley/testfile

Similarly, removing the testfile and running ls -l ~/testfile on each node should 
give a 'No such file or directory' error.

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~# rm testfile
        sgeadmin@domU-12-31-38-00-A0-61:~# ssh node001 ls -l ~/testfile
        ls: cannot access /home/jtriley/testfile: No such file or directory

Assuming you get similar results to the above for all nodes, /home is properly NFS 
mounted across the cluster.

Verify scratch space
--------------------
Each node should be set up with approximately 140GB of local scratch space for writing 
temporary files instead of storing temporary files on NFS. The location of the scratch 
space is /scratch/CLUSTER_USER. So, for this example the local scratch for 
CLUSTER_USER=sgeadmin is /scratch/sgeadmin.

To verify this, login to the master and run ls -l /scratch.

.. code-block:: none

        $ starcluster -m
        root@domU-12-31-38-00-A0-61:/# ls -l /scratch/
        total 0
        lrwxrwxrwx 1 root root 13 2009-09-09 14:34 sgeadmin -> /mnt/sgeadmin

From the output above we see that /scratch/sgeadmin has been symbolically linked 
to /mnt/sgeadmin

Next we run the df command to verify ~140GB is available on /mnt (and thus 
/mnt/sgeadmin)

.. code-block:: none

        root@domU-12-31-38-00-A0-61:/# df -h
        Filesystem Size Used Avail Use% Mounted on
        ...
        /dev/sda2 147G 188M 140G 1% /mnt
        ...
        sgeadmin@domU-12-31-38-00-A0-61:~$

Compile and run a "Hello World" OpenMPI program
-------------------------------------------------
Below is a simple Hello World program in MPI (retrieved from here)

.. code-block:: c

        #include not found stdio.h /* printf and BUFSIZ defined there */
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
compile and run the code across the cluster like so:

.. code-block:: none

        $ starcluster -m
        root@domU-12-31-38-00-A0-61:~# su - sgeadmin
        sgeadmin@domU-12-31-38-00-A0-61:~$ mpicc helloworldmpi.c -o helloworldmpi
        sgeadmin@domU-12-31-38-00-A0-61:~$ mpirun -n 2 -host master,node001 ./helloworldmpi
        domU-12-31-38-00-A0-61: hello world from process 0 of 2
        domU-12-31-38-00-A2-43: hello world from process 1 of 2
        sgeadmin@domU-12-31-38-00-A0-61:~$

Obviously if you have more nodes, the -host mater,node001 list specified will 
need to be extended. You can also create a hostfile instead of listing each 
node for OpenMPI to use that looks like:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ cat /home/sgeadmin/hostfile
        master
        node001

After creating this hostfile, you can now call mpirun with less options:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ mpirun -n 2 -hostfile /home/sgeadmin/hostfile ./helloworldmpi
        domU-12-31-38-00-A0-61: hello world from process 0 of 2
        domU-12-31-38-00-A2-43: hello world from process 1 of 2
        sgeadmin@domU-12-31-38-00-A0-61:~$

Sun Grid Engine (SGE) QuickStart
--------------------------------
Submit a Simple Job through Sun Grid Engine
Submit a job that runs hostname on a single node to Sun Grid Engine

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qsub -V -b y -cwd hostname
        Your job 1 ("hostname") has been submitted

The -V option to qsub states that the job should have the same environment 
variables as the shell executing qsub (recommended)

The -b option to qsub states that the command being executed could be a single 
binary executable or a bash script. In this case the command 'hostname' is a 
single binary.

The -cwd option to qsub tells Sun Grid Engine that the job should be executed in 
the same directory that qsub was called.

The last argument to qsub is the command to be executed (in this case 'hostname')

Monitoring Jobs in the Queue
----------------------------

Now that our job has been submitted, let's take a look at the job's status in 
the queue using the command 'qstat':

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        job-ID prior name user state submit/start at queue slots ja-task-ID
        -----------------------------------------------------------------------------------------
        1 0.00000 hostname sgeadmin qw 09/09/2009 14:58:00 1
        sgeadmin@domU-12-31-38-00-A0-61:~$

From this output, we can see that the job is in the *qw* state which stands for 
'queued and waiting'. After a few seconds, the job will transition into a *r*, 
or 'running', state.

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        job-ID  prior   name       user         state submit/start at     queue  slots ja-task-ID 
        -----------------------------------------------------------------------------------------
        1 0.00000 hostname   sgeadmin     r     09/09/2009 14:58:14                1        
        sgeadmin@domU-12-31-38-00-A0-61:~$ 

Once the job has finished, the job will be removed from the queue and will no 
longer appear in the output of qstat:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        sgeadmin@domU-12-31-38-00-A0-61:~$

Viewing a Job's Output
----------------------

Sun Grid Engine creates stdout and stderr files in the job's working directory 
for each job executed. If any additional files are created during a job's execution, 
they will also be located in the job's working directory unless explicitly saved 
elsewhere. 

The job's stdout and stderr files are named after the job with the extension ending 
in the job's number. 

For the simple job submitted above we have:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ ls hostname.*
        hostname.e1 hostname.o1
        sgeadmin@domU-12-31-38-00-A0-61:~$ cat hostname.o1
        domU-12-31-38-00-A2-43
        sgeadmin@domU-12-31-38-00-A0-61:~$ cat hostname.e1
        sgeadmin@domU-12-31-38-00-A0-61:~$

Notice that Sun Grid Engine automatically named the job 'hostname' and created two 
output files: hostname.e1 and hostname.o1. The 'e' stands for stderr and the 'o' for stdout. 
The 1 at the end of the files' extension is the job number. So if the job had been named 
'my_new_job' and was job #23 submitted, the output files would look like:

.. code-block:: none

        my_new_job.e23 my_new_job.o23

Monitoring Cluster Usage
------------------------
After a while you may be curious to view the load on Sun Grid Engine. To do this, 
we use the qhost command:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qhost
        HOSTNAME ARCH NCPU LOAD MEMTOT MEMUSE SWAPTO SWAPUS
        -------------------------------------------------------------------------------
        global - - - - - - -
        domU-12-31-38-00-A0-61 lx24-x86 1 0.00 1.7G 62.7M 896.0M 0.0
        domU-12-31-38-00-A2-43 lx24-x86 1 0.00 1.7G 47.8M 896.0M 0.0

The output shows the architecture (ARCH), number of cpus (NCPU), the current load (LOAD), 
total memory (MEMTOT), and currently used memory (MEMUSE) and swap space (SWAPTO) for each node.

You can also view the average load (load_avg) per node using the '-f' option to qstat:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat -f
        queuename qtype resv/used/tot. load_avg arch states
        ---------------------------------------------------------------------------------
        all.q@domU-12-31-38-00-A0-61.c BIP 0/0/1 0.00 lx24-x86
        ---------------------------------------------------------------------------------
        all.q@domU-12-31-38-00-A2-43.c BIP 0/0/1 0.00 lx24-x86
        sgeadmin@domU-12-31-38-00-A0-61:~$

Creating a Job Script
---------------------
In the 'Submit a Simple Job' section we submitted a single command 'hostname'. 
This is useful for simple jobs but for more complex jobs where we need to incorporate 
some logic we can use a so-called 'job script'. A 'job script' is essentially a bash 
script that contains some logic and executes any number of external programs/scripts:

.. code-block:: bash

        #!/bin/bash
        echo "hello from job script!"
        echo "the date is" `date`
        echo "here's /etc/hosts contents:"
        cat /etc/hosts
        echo "finishing job :D"

As you can see, this script simply executes a few commands (such as echo, date, cat, etc) 
and exits. Anything printed to the screen will be put in the job's stdout file by Sun Grid Engine.

Since this is just a bash script, you can put any form of logic necessary in the job script 
(ie if statements, while loops, for loops, etc) and you may call any number of external programs 
needed to complete the job.

Let's see how you run this new job script. Save the script above to /home/sgeadmin/jobscript.sh 
on your StarCluster and execute the following as the sgeadmin user:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qsub -V jobscript.sh
        Your job 6 ("jobscript.sh") has been submitted

Now that the job has been submitted, let's call qstat periodically until the job has finished 
since this job should only take a second to run once it's executed:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        job-ID prior name user state submit/start at queue slots ja-task-ID
        -----------------------------------------------------------------------------------------
        6 0.00000 jobscript. sgeadmin qw 09/09/2009 16:18:43 1

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        job-ID prior name user state submit/start at queue slots ja-task-ID
        -----------------------------------------------------------------------------------------
        6 0.00000 jobscript. sgeadmin qw 09/09/2009 16:18:43 1

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        job-ID prior name user state submit/start at queue slots ja-task-ID
        -----------------------------------------------------------------------------------------
        6 0.00000 jobscript. sgeadmin qw 09/09/2009 16:18:43 1

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        job-ID prior name user state submit/start at queue slots ja-task-ID
        -----------------------------------------------------------------------------------------
        6 0.00000 jobscript. sgeadmin qw 09/09/2009 16:18:43 1

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        job-ID prior name user state submit/start at queue slots ja-task-ID
        -----------------------------------------------------------------------------------------
        6 0.55500 jobscript. sgeadmin r 09/09/2009 16:18:57 all.q@domU-12-31-38-00-A2-43.c 1

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        sgeadmin@domU-12-31-38-00-A0-61:~$

Now that the job is finished, let's take a look at the output files:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ ls jobscript.sh*
        jobscript.sh jobscript.sh.e6 jobscript.sh.o6
        sgeadmin@domU-12-31-38-00-A0-61:~$ cat jobscript.sh.o6
        hello from job script!
        the date is Wed Sep 9 16:18:57 UTC 2009
        here's /etc/hosts contents:
        # Do not remove the following line or programs that require network functionality will fail
        127.0.0.1 localhost.localdomain localhost
        10.252.167.143 domU-12-31-38-00-A0-61.compute-1.internal domU-12-31-38-00-A0-61 master
        10.252.165.173 domU-12-31-38-00-A2-43.compute-1.internal domU-12-31-38-00-A2-43 node001
        finishing job :D
        sgeadmin@domU-12-31-38-00-A0-61:~$ cat jobscript.sh.e6
        sgeadmin@domU-12-31-38-00-A0-61:~$

We see from looking at the output that the stdout file contains the output of the 
echo,date, and cat statements in the job script and that the stderr file is blank 
meaning there were no errors during the job's execution. Had something failed, such 
as a command not found error for example, these errors would have appeared in the 
stderr file.

Deleting a Job from the Queue
-----------------------------
What if a job is stuck in the queue, is taking too long to run, or was simply 
started with incorrect parameters? You can delete a job from the queue using the 'qdel' 
command in Sun Grid Engine. Below we launch a simple 'sleep' job that sleeps for 10 
seconds so that we can kill it using 'qdel':

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qsub -b y -cwd sleep 10
        Your job 3 ("sleep") has been submitted
        sgeadmin@domU-12-31-38-00-A0-61:~$ qdel 3
        sgeadmin has registered the job 3 for deletion

After running qdel you'll notice the job is gone from the queue:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        sgeadmin@domU-12-31-38-00-A0-61:~$
