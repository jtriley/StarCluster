active_ebs_cluster = """EBS Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or stop the EBS cluster using:

    $ starcluster stop %(cluster_name)s

This command will put all nodes into a 'stopped' state and preserve their \
local disks. The cluster can later be resumed by passing the -x option to \
the start command. Another option is to terminate the existing EBS Cluster \
using:

    $ starcluster terminate %(cluster_name)s

NOTE: Terminating an EBS cluster will destroy the local disks (volumes) \
backing the nodes.
"""

stopped_ebs_cluster = """Stopped EBS Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or start the stopped EBS cluster using:

    $ starcluster start -x %(cluster_name)s

Another option is to terminate the existing EBS Cluster using:

    $ starcluster terminate %(cluster_name)s

NOTE: Terminating an EBS cluster will destroy the local disks (volumes) \
backing the nodes.
"""

cluster_exists = """Cluster with tag name %(cluster_name)s already exists.

If the cluster is a 'stopped' EBS cluster that you wish to 'start' or if you \
have yet to configure the existing cluster nodes, pass the -x option to the \
start command:

    $ starcluster start -x %(cluster_name)s

If you wish to reconfigure the existing instances use the 'restart' command:

    $ starcluster restart %(cluster_name)s

This will reboot all of the instances and configure the cluster starting from \
scratch.

Otherwise either choose a different tag name, or terminate the existing \
cluster using:

    $ starcluster terminate %(cluster_name)s

"""

cluster_started_msg = """
The cluster is now ready to use. To login to the master node as \
root, run:

    $ starcluster sshmaster %(tag)s

When you are finished using the cluster and wish to terminate it and stop \
paying for service:

    $ starcluster terminate %(tag)s

NOTE: Terminating an EBS cluster will destroy all EBS volumes backing the \
nodes.

Alternatively, if the cluster uses EBS instances, you can use the 'stop' \
command to put all nodes into a 'stopped' state:

    $ starcluster stop %(tag)s

NOTE: Any data stored in ephemeral storage (usually /mnt) will be lost!

This will shutdown all nodes in the cluster and put them in a 'stopped' state \
that preserves the EBS volumes backing the nodes. A 'stopped' cluster may \
then be restarted at a later time, without losing data on the local disks, by \
passing the -x option to the 'start' command:

    $ starcluster start -x %(tag)s

This will start all 'stopped' EBS instances and reconfigure the cluster.

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
%(new_version)s when using the '%(cluster)s' cluster.\
"""
