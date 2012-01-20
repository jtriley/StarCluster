###################
StarCluster Support
###################
The StarCluster project has several ways to get support: the `user mailing
list`_, the StarCluster `github issue tracker`_, and the **#starcluster** IRC
channel on `freenode`_.

**********************
Submitting Bug Reports
**********************
If you've found a bug in StarCluster's code, please `submit a bug report`_ to
the `github issue tracker`_. In the case of an unrecoverable error, or crash,
StarCluster will create a *crash file* containing debugging logs useful for
diagnosing the issue. Below is an example of a crash due to a bug in the code::

    % starcluster start -s 2 -v mycluster
    StarCluster - (http://web.mit.edu/starcluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    >>> Using default cluster template: smallcluster
    Traceback (most recent call last):
      File "/workspace/starcluster/starcluster/cli.py", line 155, in main
        sc.execute(args)
      File "/workspace/starcluster/starcluster/commands/start.py", line 180, in execute
        scluster = self.cm.get_cluster_template(template, tag)
      File "/workspace/starcluster/starcluster/cluster.py", line 82, in get_cluster_template
        ec2_conn=self.ec2)
      File "/workspace/starcluster/starcluster/config.py", line 589, in get_cluster_template
        clust = Cluster(ec2_conn, **kwargs)
      File "/workspace/starcluster/starcluster/cluster.py", line 315, in __init__
        blah = blah
    UnboundLocalError: local variable 'blah' referenced before assignment

    !!! ERROR - Oops! Looks like you've found a bug in StarCluster
    !!! ERROR - Crash report written to: /home/myuser/.starcluster/logs/crash-report-6029.txt
    !!! ERROR - Please remove any sensitive data from the crash report
    !!! ERROR - and submit it to starcluster@mit.edu

Each time StarCluster encounters a crash, as in the example above, a new crash
report will be written to $HOME/.starcluster/logs/crash-report-$PID.txt where
*$PID* is the process id of the buggy StarCluster session. When a crash report
is generated users should first check the crash report for any sensitive data
that might need to be removed and then `submit a bug report`_ with the crash
report attached.

********************
Issues and Questions
********************
For all other issues, questions, feature requests, etc. you can either:

.. note:: It's highly preferred that bug reports are submitted to the `github
          issue tracker`_ if possible.

#. Submit a new issue to the StarCluster `github issue tracker`_ (recommended)
#. Send a report via email to the `user mailing list`_ (**please join
   the list!**)
#. Join the **#starcluster** IRC channel on `freenode`_ and ask your
   questions/issues there. If no one's around please post to the mailing list
   instead.

.. _freenode: http://freenode.net
.. _submit a bug report: https://github.com/jtriley/StarCluster/issues/new
.. _github issue tracker: https://github.com/jtriley/StarCluster/issues
.. _user mailing list: http://web.mit.edu/stardev/cluster/mailinglist.html
