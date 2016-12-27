##################################
Copying Data to and from a Cluster
##################################
StarCluster now supports conveniently copying data to and from a running
cluster via the new ``put`` and ``get`` commands. These commands provide the
same functionality as the `scp` command from OpenSSH only without the need to
specify SSH keypairs or EC2 dns names.

*******************************
Copying Data to a Cluster (put)
*******************************
To copy data from your local computer to a cluster on Amazon use the ``put``
command. Recursion will be handled automatically if necessary. By default the
``put`` command will operate on the `master` node as the `root` user::

    $ starcluster put mycluster /path/to/file/or/dir /path/on/remote/server

To copy files as a different cluster user, use the ``--user`` (``-u``) option::

    $ starcluster put mycluster --user myuser /local/path /remote/path

To copy files to a different cluster node, use the ``--node`` (``-n``) option::

    $ starcluster put mycluster --node node001 /local/path /remote/path

To copy files to multiple cluster nodes, provide comma separated nodes to the
``--multi`` (``-m``) option::

    $ starcluster put mycluster --multi master,node001 /local/path /remote/path

*********************************
Copying Data from a Cluster (get)
*********************************
To copy data from a cluster on Amazon to your local computer use the ``get``
command. Recursion will be handled automatically if necessary. By default the
``get`` command will operate on the master node as the *root* user::

    $ starcluster get mycluster /path/on/remote/server /path/to/file/or/dir

To copy files as a different cluster user, use the ``--user`` (``-u``) option::

    $ starcluster get mycluster --user myuser /remote/path /local/path

To copy files from a different cluster node, use the ``--node`` (``-n``)
option::

    $ starcluster get mycluster --node node001 /remote/path /local/path
