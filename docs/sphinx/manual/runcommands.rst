#########################################
Running Remote Commands from Command Line
#########################################
StarCluster's **sshmaster**, **sshnode**, and **sshinstance** commands now
support executing remote commands on a cluster node without logging in
interactively. This is especially useful for users looking to script these
commands. To do so simply pass the command you wish to run remotely as an
additional quoted argument to any of the **sshmaster**, **sshnode**, and
**sshinstance** commands.

For example, to check which hosts are listed in the master node's
``/etc/hosts`` file::

    $ starcluster sshmaster mycluster 'cat /etc/hosts'
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    10.10.10.1 master
    10.10.10.2 node001
    10.10.10.3 node002

or to quickly check the files in a given directory on ``node001``::

    $ starcluster sshnode mycluster node001 'ls -l /data'
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    drwxr-xr-x 4 root root  4096 Nov  5 00:06 data-2011
    drwxr-xr-x 2 root root  4096 Nov  4 14:21 data-2010
    drwxr-xr-x 2 root root  4096 Nov  4 14:23 data-2009
    drwxr-xr-x 4 root root  4096 Oct 17 13:42 data-2008

*Any* command you can run while logged into a cluster interactively can be
executed remotely from your local command line simply by quoting the remote
command and passing it as an additional argument to any of the **sshmaster**,
**sshnode**, and **sshinstance**  commands as in the above examples.

If the remote command is successful the exit code of either the **sshmaster**,
**sshnode**, or **sshinstance** command will be 0::

    $ starcluster sshmaster mycluster 'uptime'
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    00:58:12 up 1 days,  9:49,  2 users,  load average: 0.02, 0.06, 0.12
    $ echo $?
    0

Otherwise, the exit code will be identical to the remote command's non-zero
exit code::

    $ starcluster sshmaster mycluster 'uptimes2'
    StarCluster - (http://star.mit.edu/cluster)
    Software Tools for Academics and Researchers (STAR)
    Please submit bug reports to starcluster@mit.edu

    command not found: uptimes2

    !!! ERROR - command 'uptimes2' failed with status 127
    $ echo $?
    127

This allows you to use the **sshmaster**, **sshnode**, and **sshinstance**
commands in scripts and check whether or not the remote command finished
successfully.

************************************
Running X11 (Graphical) Applications
************************************
If you have OpenSSH installed and an X server you can enable X11 forwarding
over SSH using the ``--forward-x11 (-X)`` option. This allows you to run
graphical applications on the cluster and display them on your local computer.
For example, to run `xterm` on the master node of `mycluster`::

    $ starcluster sshmaster -X mycluster xterm

The ``sshnode`` command also supports the ``-X`` option::

    $ starcluster sshnode -X mycluster node001 xterm
