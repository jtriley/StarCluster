Sun Grid Engine (SGE) QuickStart
--------------------------------
Submit a Simple Job through Sun Grid Engine Submit a job that runs hostname on
a single node to Sun Grid Engine

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qsub -V -b y -cwd hostname
        Your job 1 ("hostname") has been submitted

The -V option to qsub states that the job should have the same environment
variables as the shell executing qsub (recommended)

The -b option to qsub states that the command being executed could be a single
binary executable or a bash script. In this case the command 'hostname' is a
single binary.

The -cwd option to qsub tells Sun Grid Engine that the job should be executed
in the same directory that qsub was called.

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
for each job executed. If any additional files are created during a job's
execution, they will also be located in the job's working directory unless
explicitly saved elsewhere.

The job's stdout and stderr files are named after the job with the extension
ending in the job's number.

For the simple job submitted above we have:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ ls hostname.*
        hostname.e1 hostname.o1
        sgeadmin@domU-12-31-38-00-A0-61:~$ cat hostname.o1
        domU-12-31-38-00-A2-43
        sgeadmin@domU-12-31-38-00-A0-61:~$ cat hostname.e1
        sgeadmin@domU-12-31-38-00-A0-61:~$

Notice that Sun Grid Engine automatically named the job 'hostname' and created
two output files: hostname.e1 and hostname.o1. The 'e' stands for stderr and
the 'o' for stdout. The 1 at the end of the files' extension is the job
number. So if the job had been named 'my_new_job' and was job #23 submitted,
the output files would look like:

.. code-block:: none

        my_new_job.e23 my_new_job.o23

Monitoring Cluster Usage
------------------------
After a while you may be curious to view the load on Sun Grid Engine. To do
this, we use the qhost command:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qhost
        HOSTNAME ARCH NCPU LOAD MEMTOT MEMUSE SWAPTO SWAPUS
        -------------------------------------------------------------------------------
        global - - - - - - -
        domU-12-31-38-00-A0-61 lx24-x86 1 0.00 1.7G 62.7M 896.0M 0.0
        domU-12-31-38-00-A2-43 lx24-x86 1 0.00 1.7G 47.8M 896.0M 0.0

The output shows the architecture (ARCH), number of cpus (NCPU), the current
load (LOAD), total memory (MEMTOT), and currently used memory (MEMUSE) and swap
space (SWAPTO) for each node.

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
This is useful for simple jobs but for more complex jobs where we need to
incorporate some logic we can use a so-called 'job script'. A 'job script' is
essentially a bash script that contains some logic and executes any number of
external programs/scripts:

.. code-block:: bash

        #!/bin/bash
        echo "hello from job script!"
        echo "the date is" `date`
        echo "here's /etc/hosts contents:"
        cat /etc/hosts
        echo "finishing job :D"

As you can see, this script simply executes a few commands (such as echo, date,
cat, etc) and exits. Anything printed to the screen will be put in the job's
stdout file by Sun Grid Engine.

Since this is just a bash script, you can put any form of logic necessary in
the job script (ie if statements, while loops, for loops, etc) and you may call
any number of external programs needed to complete the job.

Let's see how you run this new job script. Save the script above to
/home/sgeadmin/jobscript.sh on your StarCluster and execute the following as
the sgeadmin user:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qsub -V jobscript.sh
        Your job 6 ("jobscript.sh") has been submitted

Now that the job has been submitted, let's call qstat periodically until the
job has finished since this job should only take a second to run once it's
executed:

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

We see from looking at the output that the stdout file contains the output of
the echo,date, and cat statements in the job script and that the stderr file is
blank meaning there were no errors during the job's execution. Had something
failed, such as a command not found error for example, these errors would have
appeared in the stderr file.

Deleting a Job from the Queue
-----------------------------
What if a job is stuck in the queue, is taking too long to run, or was simply
started with incorrect parameters? You can delete a job from the queue using
the 'qdel' command in Sun Grid Engine. Below we launch a simple 'sleep' job
that sleeps for 10 seconds so that we can kill it using 'qdel':

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qsub -b y -cwd sleep 10
        Your job 3 ("sleep") has been submitted
        sgeadmin@domU-12-31-38-00-A0-61:~$ qdel 3
        sgeadmin has registered the job 3 for deletion

After running qdel you'll notice the job is gone from the queue:

.. code-block:: none

        sgeadmin@domU-12-31-38-00-A0-61:~$ qstat
        sgeadmin@domU-12-31-38-00-A0-61:~$
