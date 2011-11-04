##################################
Copying Data to and from a Cluster
##################################
StarCluster now supports conveniently copying data to and from a running
cluster via the new **put** and **get** commands. These commands provide the
same functionality as the *scp* command from OpenSSH only without the need to
specify SSH keypairs or EC2 dns names.

****************************
Enable Experimental Features
****************************
For now the **put** and **get** commands are experimental which means you will
need to set ``enable_experimental`` to ``True`` in the **[global]** section of
the config in order to use them::

    [global]
    enable_experimental=True

Below are a few examples of how to use the **put** and **get** commands.

.. note::

    All of the examples below automatically handle recursion without requiring
    any extra command line options

*******************************
Copying Data to a Cluster (put)
*******************************
To copy data from your local computer to a cluster on Amazon use the **put**
command. Recursion will be handled automatically if necessary. By default the
**put** command will operate on the master node as the *root* user::

    $ starcluster put mycluster /path/to/file/or/dir /path/on/remote/server

Copy a file or directory to the master as a normal user
=======================================================
By default the **put** command copies files as the root user. To copy files as
a different cluster user, use the ``--user`` (``-u``) option::

    $ starcluster put mycluster --user myuser /local/path /remote/path

Copy a file or directory to a cluster node
==========================================
By default the **put** command copies files to the master node. To copy files
to a different cluster node, use the ``--node`` (``-n``) option::

    $ starcluster put mycluster --node node001 /local/path /remote/path

*********************************
Copying Data from a Cluster (get)
*********************************
To copy data from a cluster on Amazon to your local computer use the **get**
command. Recursion will be handled automatically if necessary. By default the
**get** command will operate on the master node as the *root* user::

    $ starcluster get mycluster /path/on/remote/server /path/to/file/or/dir

Copy a file or directory from the master as a normal user
=========================================================
By default the **get** command copies files as the root user. To copy files as
a different cluster user, use the ``--user`` (``-u``) option::

    $ starcluster get mycluster --user myuser /remote/path /local/path

Copy a file or directory from a cluster node
============================================
By default the **get** command copies files from the master node. To copy files
from a different cluster node, use the ``--node`` (``-n``) option::

    $ starcluster get mycluster --node node001 /remote/path /local/path
