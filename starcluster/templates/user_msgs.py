#!/usr/bin/env python

active_ebs_cluster = """EBS Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or stop the EBS cluster using:

  $ starcluster stop %(cluster_name)s

This command will put all nodes into a 'stopped' state and preserve their \
local disks. The cluster can later be resumed by passing the -x option to \
the start command. (NOTE: You pay for the local disks when the nodes are \
not running)

Another option is to terminate the existing EBS Cluster using:

  $ starcluster terminate %(cluster_name)s

NOTE: Terminating an EBS cluster will destroy the local disks (volumes) \
backing the nodes.
"""

stopped_ebs_cluster = """Stopped EBS Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or start the stopped EBS cluster using:

  $ starcluster start %(cluster_name)s -x

Another option is to terminate the existing EBS Cluster using:

  $ starcluster terminate %(cluster_name)s

NOTE: Terminating an EBS cluster will destroy the local disks (voluems) \
backing the nodes.
"""

cluster_exists = """Cluster with tag name %(cluster_name)s already exists.

If you want to reconfigure the existing instances use the 'restart' command:

  $ starcluster restart %(cluster_name)s

This will reboot all of the instances and configure the cluster starting from \
scratch.

Otherwise either choose a different tag name, or terminate the existing \
cluster using:

  $ starcluster terminate %(cluster_name)s

"""

cluster_started_msg = """

The cluster has been started and configured.
Login to the master node as root by running:

    $ starcluster sshmaster %(tag)s

When you are finished using the cluster, run:

    $ starcluster stop %(tag)s

to shutdown the cluster and stop paying for service.

If this cluster uses EBS instances then the 'stop' command above will put all \
nodes into a 'stopped' state. The cluster may then be restarted at a later \
time, without losing data, by passing the -x option to the 'start' command.

To completely terminate an EBS cluster:

    $ starcluster terminate %(tag)s

NOTE: Terminating an EBS cluster will destroy all volumes backing the nodes.
"""

spotmsg = """SPOT INSTANCES ARE NOT GUARANTEED TO COME UP

Spot instances can take a long time to come up and may not come up at all \
depending on the current AWS load and your max spot bid price.

StarCluster will wait indefinitely until all instances (%(size)s) come up. \
If this takes too long, you can cancel the start command using CTRL-C. \
You can then resume the start command later on using the --no-create (-x) \
option:

   $ starcluster start -x %(tag)s

This will use the existing spot instances launched previously and continue \
starting the cluster. If you don't wish to wait on the cluster any longer \
after pressing CTRL-C simply terminate the cluster using the 'terminate' \
command.\
"""

version_mismatch = """\
The cluster '%(cluster)s' was created with a newer version of StarCluster \
(%(new_version)s). You're currently using version %(old_version)s.

This may or may not be a problem depending on what's changed between these \
versions, however, it's highly recommended that you use version \
%(old_version)s when using the '%(cluster)s' cluster.\
"""
