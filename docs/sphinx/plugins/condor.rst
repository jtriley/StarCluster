.. _condor-plugin:

#############
Condor Plugin
#############
.. note::

    Condor is only available on the latest StarCluster 11.10 Ubuntu-based AMIs
    and above. See `starcluster listpublic` for a list of available AMIs.

To configure a condor pool on your cluster you must first define the
``condor`` plugin in your config file:

.. code-block:: ini

    [plugin condor]
    setup_class = starcluster.plugins.condor.CondorPlugin

After defining the plugin in your config, add the ``condor`` plugin to the list
of plugins in one of your cluster templates:

.. code-block:: ini

    [cluster smallcluster]
    plugins = condor

************************
Using the Condor Cluster
************************
Condor jobs cannot be submitted by the ``root`` user. Instead you must login to
the cluster as the normal ``CLUSTER_USER``::

    $ starcluster sshmaster mycluster -u myuser

***************
Submitting Jobs
***************

.. warning::

    The "parallel" universe currently does not work. This should be
    resolved in a future release.

To submit a job you must first create a job script. Below is a simple example
that submits a job which sleeps for 5 minutes::

    Universe   = vanilla
    Executable = /bin/sleep
    Arguments  = 300
    Log        = sleep.log
    Output     = sleep.out
    Error      = sleep.error
    Queue

The above job will run ``/bin/sleep`` passing ``300`` as the first argument.
Condor messages will be logged to ``$PWD/sleep.log`` and the job's standard
output and standard error will be saved to ``$PWD/sleep.out`` and
``$PWD/sleep.error`` respectively where ``$PWD`` is the directory from which
the job was originally submitted. Save the job script to a file, say
``job.txt``, and use the ``condor_submit`` command to submit the job::

    $ condor_submit job.txt
    Submitting job(s).
    1 job(s) submitted to cluster 8.

From the output above we see the job has been submitted to the cluster as job
8. Let's submit this job once more in order to test that multiple jobs can be
successfully distributed across the cluster by Condor::

    $ condor_submit job.txt
    Submitting job(s).
    1 job(s) submitted to cluster 9.

The last job was submitted as job 9. The next step is to monitor these jobs
until they're finished.

*********************
Monitoring Job Status
*********************
To monitor the status of your Condor jobs use the ``condor_q`` command::

    $ condor_q
    -- Submitter: master : <10.220.226.138:52585> : master
     ID      OWNER            SUBMITTED     RUN_TIME ST PRI SIZE CMD
       8.0   myuser         12/12 21:31   0+00:06:40 R  0   0.0  sleep 300
       9.0   myuser         12/12 21:31   0+00:05:56 R  0   0.0  sleep 300

    2 jobs; 0 idle, 2 running, 0 held

From the output above we see that both jobs are currently running. To find out
which cluster nodes the jobs are running on pass the ``-run`` option::

    $ condor_q -run
    -- Submitter: master : <10.220.226.138:52585> : master
     ID      OWNER            SUBMITTED     RUN_TIME HOST(S)
       8.0   myuser         12/12 21:31   0+00:05:57 master
       9.0   myuser         12/12 21:31   0+00:05:13 node001

Here we see that job 8 is running on the ``master`` and job 9 is running on
``node001``. If your job is taking too long to run you can diagnose the issue
by passing the ``-analyze`` option to ``condor_q``::

    $ condor_q -analyze

This will give you verbose output showing which scheduling conditions failed
and why.

***************
Canceling Jobs
***************
In some cases you may need to cancel queued or running jobs either because of
an error in your job script or simply because you wish to change job
parameters. Whatever the case may be you can cancel jobs by passing the job ids
to ``condor_rm``::

    $ condor_rm 9
    Cluster 9 has been marked for removal.

The above example removes job 9 from the condor queue.
