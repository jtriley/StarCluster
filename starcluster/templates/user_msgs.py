#!/usr/bin/env python

cluster_started_msg = """

The cluster has been started and configured.
Login to the master node as root by running:

    $ starcluster sshmaster %(tag)s

When you are finished using the cluster, run:

    $ starcluster stop %(tag)s

to shutdown the cluster and stop paying for service.

If this cluster uses EBS instances then the 'stop' command
above will put all nodes into a 'stopped' state. The cluster
may then be restarted at a later time, without losing data,
by passing the -x option to the 'start' command.

To completely terminate an EBS cluster:

    $ starcluster terminate %(tag)s
"""

spotmsg = """SPOT INSTANCES ARE NOT GUARANTEED TO COME UP

Spot instances can take a long time to come up and may not come
up at all depending on the current AWS load and your max spot bid
price.

StarCluster will wait indefinitely until all instances come up.
If this takes too long, you can cancel the start command using
CTRL-C and manually wait for the spot instances to come up by
periodically checking the output of:

   $ starcluster listclusters %(tag)s

Once all instances (%(size)d) show up in the output of the 'listclusters'
command above, re-execute this same start command with the
--no-create option:

   $ starcluster %(cmd)s

This will use the existing spot instances launched previously and
continue starting the cluster.
"""
