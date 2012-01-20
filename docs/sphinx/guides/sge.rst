Sun Grid Engine (SGE) QuickStart
================================

The Sun Grid Engine queuing system is useful when you have a lot of tasks to
execute and want to distribute the tasks over a cluster of machines. For
example, you might need to run hundreds of simulations/experiments with varying
parameters or need to convert 300 videos from one format to another. Using a
queuing system in these situations has the following advantages:

* **Scheduling** - allows you to schedule a virtually unlimited amount of work
  to be performed when resources become available. This means you can simply
  submit as many tasks (or *jobs*) as you like and let the queuing system
  handle executing them all.
* **Load Balancing** - automatically distributes tasks across the cluster such
  that any one node doesn't get overloaded compared to the rest.
* **Monitoring/Accounting** - ability to monitor all submitted jobs and query
  which cluster nodes they're running on, whether they're finished, encountered
  an error, etc. Also allows querying job history to see which tasks were
  executed on a given date, by a given user, etc.

.. note::
    Of course, just because a queuing system is installed doesn't mean you
    *have* to use it at all. You can run your tasks across the cluster in any
    way you see fit and the queuing system should not interfere.  However, you
    will most likely end up needing to implement the above features in some
    fashion in order to optimally utilize the cluster.

Submitting Jobs
---------------
A job in SGE represents a task to be performed on a node in the cluster and
contains the command line used to start the task. A job may have specific
resource requirements but in general should be agnostic to *which* node in the
cluster it runs on as long as its resource requirements are met.

.. note::
    All jobs require *at least* one available slot on a node in the cluster to
    run.

Submitting jobs is done using the *qsub* command. Let's try submitting a simple
job that runs the *hostname* command on a given cluster node::

    sgeadmin@master:~$ qsub -V -b y -cwd hostname
    Your job 1 ("hostname") has been submitted

* The **-V** option to *qsub* states that the job should have the same
  environment variables as the shell executing *qsub* (*recommended*)

* The **-b** option to *qsub* states that the command being executed could be a
  single binary executable or a bash script. In this case the command
  *hostname* is a single binary. This option takes a *y* or *n* argument
  indicating either *yes* the command is a binary or *no* it is not a binary.

* The **-cwd** option to *qsub* tells Sun Grid Engine that the job should be
  executed in the same directory that *qsub* was called.

* The last argument to *qsub* is the command to be executed (*hostname* in this
  case)

Notice that the *qsub* command, when successful, will print the job number to
stdout. You can use the job number to monitor the job's status and progress
within the queue as we'll see in the next section.

Monitoring Jobs in the Queue
----------------------------
Now that our job has been submitted, let's take a look at the job's status in
the queue using the command *qstat*::

    sgeadmin@master:~$ qstat
    job-ID prior name user state submit/start at queue slots ja-task-ID
    -------------------------------------------------------------------
    1 0.00000 hostname sgeadmin qw 09/09/2009 14:58:00 1
    sgeadmin@master:~$

From this output, we can see that the job is in the **qw** state which stands
for *queued and waiting*. After a few seconds, the job will transition into a
**r**, or *running*, state at which point the job will begin executing::

    sgeadmin@master:~$ qstat
    job-ID  prior   name       user         state submit/start at     queue  slots ja-task-ID
    -----------------------------------------------------------------------------------------
    1 0.00000 hostname   sgeadmin     r     09/09/2009 14:58:14                1
    sgeadmin@master:~$

Once the job has finished, the job will be removed from the queue and will no
longer appear in the output of *qstat*::

    sgeadmin@master:~$ qstat
    sgeadmin@master:~$

Now that the job has finished let's move on to the next section to see how we
view a job's output.

Viewing a Job's Output
----------------------

Sun Grid Engine creates stdout and stderr files in the job's working directory
for each job executed. If any additional files are created during a job's
execution, they will also be located in the job's working directory unless
explicitly saved elsewhere.

The job's stdout and stderr files are named after the job with the extension
ending in the job's number.

For the simple job submitted above we have::

    sgeadmin@master:~$ ls hostname.*
    hostname.e1 hostname.o1
    sgeadmin@master:~$ cat hostname.o1
    node001
    sgeadmin@master:~$ cat hostname.e1
    sgeadmin@master:~$

Notice that Sun Grid Engine automatically named the job *hostname* and created
two output files: hostname.e1 and hostname.o1. The **e** stands for stderr and
the **o** for stdout. The **1** at the end of the files' extension is the job
number. So if the job had been named *my_new_job* and was job #23 submitted,
the output files would look like::

    my_new_job.e23 my_new_job.o23

Monitoring Cluster Usage
------------------------
After a while you may be curious to view the load on Sun Grid Engine. To do
this, we use the *qhost* command::

    sgeadmin@master:~$ qhost
    HOSTNAME ARCH NCPU LOAD MEMTOT MEMUSE SWAPTO SWAPUS
    -------------------------------------------------------------------------------
    global - - - - - - -
    master lx24-x86 1 0.00 1.7G 62.7M 896.0M 0.0
    node001 lx24-x86 1 0.00 1.7G 47.8M 896.0M 0.0

The output shows the architecture (**ARCH**), number of cpus (**NCPU**), the
current load (**LOAD**), total memory (**MEMTOT**), and currently used memory
(**MEMUSE**) and swap space (**SWAPTO**) for each node.

You can also view the average load (load_avg) per node using the '-f' option to
*qstat*::

    sgeadmin@master:~$ qstat -f
    queuename qtype resv/used/tot. load_avg arch states
    ---------------------------------------------------------------------------------
    all.q@master.c BIP 0/0/1 0.00 lx24-x86
    ---------------------------------------------------------------------------------
    all.q@node001.c BIP 0/0/1 0.00 lx24-x86

Creating a Job Script
---------------------
In the 'Submitting a Job' section we submitted a single command *hostname*.
This is useful for simple jobs but for more complex jobs where we need to
incorporate some logic we can use a so-called *job script*. A *job script* is
essentially a bash script that contains some logic and executes any number of
external programs/scripts::

    #!/bin/bash
    echo "hello from job script!"
    echo "the date is" `date`
    echo "here's /etc/hosts contents:"
    cat /etc/hosts
    echo "finishing job :D"

As you can see, this script simply executes a few commands (such as echo, date,
cat, etc.) and exits. Anything printed to the screen will be put in the job's
stdout file by Sun Grid Engine.

Since this is just a bash script, you can put any form of logic necessary in
the job script (i.e. if statements, while loops, for loops, etc.) and you may
call any number of external programs needed to complete the job.

Let's see how you run this new job script. Save the script above to
/home/sgeadmin/jobscript.sh on your StarCluster and execute the following as
the sgeadmin user::

    sgeadmin@master:~$ qsub -V jobscript.sh
    Your job 6 ("jobscript.sh") has been submitted

Now that the job has been submitted, let's call *qstat* periodically until the
job has finished since this job should only take a second to run once it's
executed::

    sgeadmin@master:~$ qstat
    job-ID prior name user state submit/start at queue slots ja-task-ID
    -------------------------------------------------------------------
    6 0.00000 jobscript. sgeadmin qw 09/09/2009 16:18:43 1

    sgeadmin@master:~$ qstat
    job-ID prior name user state submit/start at queue slots ja-task-ID
    -------------------------------------------------------------------
    6 0.00000 jobscript. sgeadmin qw 09/09/2009 16:18:43 1

    sgeadmin@master:~$ qstat
    job-ID prior name user state submit/start at queue slots ja-task-ID
    -------------------------------------------------------------------
    6 0.00000 jobscript. sgeadmin qw 09/09/2009 16:18:43 1

    sgeadmin@master:~$ qstat
    job-ID prior name user state submit/start at queue slots ja-task-ID
    -------------------------------------------------------------------
    6 0.00000 jobscript. sgeadmin qw 09/09/2009 16:18:43 1

    sgeadmin@master:~$ qstat
    job-ID prior name user state submit/start at queue slots ja-task-ID
    -------------------------------------------------------------------
    6 0.55500 jobscript. sgeadmin r 09/09/2009 16:18:57 all.q@node001.c 1

    sgeadmin@master:~$ qstat
    sgeadmin@master:~$

Now that the job is finished, let's take a look at the output files::

    sgeadmin@master:~$ ls jobscript.sh*
    jobscript.sh jobscript.sh.e6 jobscript.sh.o6
    sgeadmin@master:~$ cat jobscript.sh.o6
    hello from job script!
    the date is Wed Sep 9 16:18:57 UTC 2009
    here's /etc/hosts contents:
    # Do not remove the following line or programs that require network functionality will fail
    127.0.0.1 localhost.localdomain localhost
    10.252.167.143 master
    10.252.165.173 node001
    finishing job :D
    sgeadmin@master:~$ cat jobscript.sh.e6
    sgeadmin@master:~$

We see from looking at the output that the stdout file contains the output of
the echo, date, and cat statements in the job script and that the stderr file
is blank meaning there were no errors during the job's execution. Had something
failed, such as a command not found error for example, these errors would have
appeared in the stderr file.

Deleting a Job from the Queue
-----------------------------
What if a job is stuck in the queue, is taking too long to run, or was simply
started with incorrect parameters? You can delete a job from the queue using
the *qdel* command in Sun Grid Engine. Below we launch a simple 'sleep' job
that sleeps for 10 seconds so that we can kill it using *qdel*::

    sgeadmin@master:~$ qsub -b y -cwd sleep 10
    Your job 3 ("sleep") has been submitted
    sgeadmin@master:~$ qdel 3
    sgeadmin has registered the job 3 for deletion

After running *qdel* you'll notice the job is gone from the queue::

    sgeadmin@master:~$ qstat
    sgeadmin@master:~$

OpenMPI and Sun Grid Engine
---------------------------
.. note::
    OpenMPI must be compiled with SGE support (--with-sge) to make use of the
    tight-integration between OpenMPI and SGE as documented in this section.
    This is the case on all of StarCluster's public AMIs.

OpenMPI supports tight integration with Sun Grid Engine. This integration
allows Sun Grid Engine to handle assigning hosts to parallel jobs and to
properly account for parallel jobs.

OpenMPI Parallel Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
StarCluster by default sets up a parallel environment, called "orte", that has
been configured for OpenMPI integration within SGE and has a number of *slots*
equal to the total number of processors in the cluster.  You can inspect the
SGE parallel environment by running::

    sgeadmin@ip-10-194-13-219:~$ qconf -sp orte
    pe_name            orte
    slots              16
    user_lists         NONE
    xuser_lists        NONE
    start_proc_args    /bin/true
    stop_proc_args     /bin/true
    allocation_rule    $round_robin
    control_slaves     TRUE
    job_is_first_task  FALSE
    urgency_slots      min
    accounting_summary FALSE

This is the default configuration for a two-node, c1.xlarge cluster (16 virtual
cores).

Round Robin vs Fill Up Modes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Notice the *allocation_rule* setting in the output of the *qconf* command in
the previous section. This defines how to assign *slots* to a job. By default
StarCluster configures *round_robin* allocation.  This means that if a job
requests 8 *slots* for example, it will go to the first machine, grab a single
slot if available, move to the next machine and grab a single slot if
available, and so on wrapping around the cluster again if necessary to allocate
8 *slots* to the job.

You can also configure the parallel environment to try and localize *slots* as
much as possible using the *fill_up* allocation rule. With this rule, if a user
requests 8 *slots* and a single machine has 8 *slots* available, that job will
run entirely on one machine. If 5 *slots* are available on one host and 3 on
another, it will take all 5 on that host, and all 3 on the other host. In other
words, this rule will greedily take all *slots* on a given node until the slot
requirement for the job is met.

You can switch between *round_robin* and *fill_up* modes using the following
command::

    $ qconf -mp orte

This will open up vi (or any editor defined in *EDITOR* env variable) and let
you edit the parallel environment settings. To change from *round_robin* to
*fill_up* in the above example, change the *allocation_rule* line from::

    allocation_rule    $round_robin

to::

    allocation_rule    $fill_up

After making the change and saving the file you can verify your settings using::

    sgeadmin@ip-10-194-13-219:~$ qconf -sp orte
    pe_name            orte
    slots              16
    user_lists         NONE
    xuser_lists        NONE
    start_proc_args    /bin/true
    stop_proc_args     /bin/true
    allocation_rule    $fill_up
    control_slaves     TRUE
    job_is_first_task  FALSE
    urgency_slots      min
    accounting_summary FALSE

Submitting OpenMPI Jobs using a Parallel Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The general workflow for running MPI code is:

1. Compile the code using mpicc, mpicxx, mpif77, mpif90, etc.
2. Copy the resulting executable to the same path on all nodes or to an
   NFS-shared location on the master node

.. note::
    It is important that the path to the executable is *identical* on all nodes
    for mpirun to correctly launch your parallel code. The easiest approach is
    to copy the executable somewhere under /home on the master node since /home
    is NFS-shared across all nodes in the cluster.

3. Run the code on *X* number of machines using::

    $ mpirun -np X -hostfile myhostfile ./mpi-executable arg1 arg2 [...]

where the hostfile looks something like::

    $ cat /path/to/hostfile
    master  slots=2
    node001 slots=2
    node002 slots=2
    node003 slots=2

However, when using an SGE parallel environment with OpenMPI **you no longer
have to specify the -np, -hostfile, -host, etc. options to mpirun**. This is
because SGE will *automatically* assign hosts and processors to be used by
OpenMPI for your job. You also do not need to pass the --byslot and --bynode
options to mpirun given that these mechanisms are now handled by the *fill_up*
and *round_robin* modes specified in the SGE parallel environment.

Instead of using the above formulation create a simple job script that contains
a very simplified mpirun call::

    $ cat myjobscript.sh
    mpirun /path/to/mpi-executable arg1 arg2 [...]

Then submit the job using the *qsub* command and the *orte* parallel
environment automatically configured for you by StarCluster::

    $ qsub -pe orte 24 ./myjobscript.sh

The **-pe** option species which parallel environment to use and how many
*slots* to request. The above example requests 24 *slots* (or processors) using
the *orte* parallel environment. The parallel environment automatically takes
care of distributing the MPI job amongst the SGE nodes using the
*allocation_rule* defined in the environment's settings.

You can also do this without a job script like so::

    $ cd /path/to/executable
    $ qsub -b y -cwd -pe orte 24 mpirun ./mpi-executable arg1 arg2 [...]
