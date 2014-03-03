# Copyright 2009-2013 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

active_ebs_cluster = """EBS Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or terminate the existing EBS cluster \
using:

    $ starcluster terminate %(cluster_name)s

WARNING: Terminating an EBS cluster will destroy the local disks (volumes) \
backing the nodes.

If you encountered an issue while starting or using '%(cluster_name)s' you \
can reboot and reconfigure the cluster using the 'restart' command:

    $ starcluster restart %(cluster_name)s

This will reboot all existing nodes and completely reconfigure the cluster \
without wasting instance hours.

"""

stopped_ebs_cluster = """Stopped EBS Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or start the 'stopped' cluster using:

    $ starcluster start -x %(cluster_name)s

Another option is to terminate the stopped EBS Cluster using:

    $ starcluster terminate %(cluster_name)s

WARNING: Terminating an EBS cluster will destroy the local disks (volumes) \
backing the nodes.
"""

cluster_exists = """Cluster '%(cluster_name)s' already exists.

Either choose a different tag name, or terminate the existing cluster using:

    $ starcluster terminate %(cluster_name)s

If you encountered an issue while starting or using '%(cluster_name)s' you \
can reboot and reconfigure the cluster using the 'restart' command:

    $ starcluster restart %(cluster_name)s

This will reboot all existing nodes and completely reconfigure the cluster \
without wasting instance hours.

"""

cluster_started_msg = """
The cluster is now ready to use. To login to the master node as root, run:

    $ starcluster sshmaster %(tag)s

If you're having issues with the cluster you can reboot the instances and \
completely reconfigure the cluster from scratch using:

    $ starcluster restart %(tag)s

When you're finished using the cluster and wish to terminate it and stop \
paying for service:

    $ starcluster terminate %(tag)s

Alternatively, if the cluster uses EBS instances, you can use the 'stop' \
command to shutdown all nodes and put them into a 'stopped' state preserving \
the EBS volumes backing the nodes:

    $ starcluster stop %(tag)s

WARNING: Any data stored in ephemeral storage (usually /mnt) will be lost!

You can activate a 'stopped' cluster by passing the -x option to the 'start' \
command:

    $ starcluster start -x %(tag)s

This will start all 'stopped' nodes and reconfigure the cluster.
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

authkeys_access_denied = """\
Remote SSH access for user '%(user)s' denied via authorized_keys

This usually means the AMI you're using has been configured to deny SSH \
access for the '%(user)s' user. Either fix your AMI or use one of the \
StarCluster supported AMIs. You can obtain a list of StarCluster supported \
AMIs using the 'listpublic' command:

    $ starcluster listpublic

If you need to customize one of the StarCluster supported AMIs simply launch \
an instance of the AMI, login remotely, configure the instance, and then use \
the 'ebsimage' command to create a new EBS AMI from the instance with your \
changes:

    $ starcluster ebsimage <instance-id> <image-name>

Pass the --help flag to the 'ebsimage' command for more details.
"""

public_ips_disabled = """\
PUBLIC IPS HAVE BEEN DISABLED!!!

This means StarCluster must be executed from a machine within the cluster's VPC
(%(vpc_id)s) otherwise it will hang forever trying to connect to the instances.
"""
