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

from starcluster.logger import log
from starcluster import exception

from completers import ClusterCompleter


class CmdStop(ClusterCompleter):
    """
    stop [options] <cluster_tag> ...

    Stop a running EBS-backed cluster

    Example:

        $ starcluster stop mycluster

    The above command will put all flat-rate EBS-backed nodes in 'mycluster'
    into a 'stopped' state preserving the local disks. You can then use the
    start command with the -x (--no-create) option to resume the cluster later
    on without losing data on the local disks:

        $ starcluster start -x mycluster

    This will 'start' all 'stopped' non-spot EBS-backed instances and
    reconfigure the cluster.

    In general, all nodes in the cluster must be 'stoppable' meaning all nodes
    are backed by flat-rate EBS-backed instances. If any 'unstoppable' nodes
    are found an error is raised. A node is 'unstoppable' if it is backed by
    either a spot or S3-backed instance.

    However, if the cluster contains a mix of 'stoppable' and 'unstoppable'
    nodes you can stop all stoppable nodes and terminate any unstoppable nodes
    using the --terminate-unstoppable (-t) option:

        $ starcluster stop --terminate-unstoppable mycluster

    This will stop all nodes that can be stopped and terminate the rest.
    """
    names = ['stop']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="Do not prompt for confirmation, "
                          "just stop the cluster")
        parser.add_option("-t", "--terminate-unstoppable",
                          dest="terminate_unstoppable", action="store_true",
                          default=False,  help="Terminate nodes that are not "
                          "stoppable (i.e. spot or S3-backed nodes)")
        parser.add_option("-f", "--force", dest="force", action="store_true",
                          default=False,  help="Stop cluster regardless of "
                          " errors if possible")

    def execute(self, args):
        if not args:
            cls = [c.cluster_tag for c in
                   self.cm.get_clusters(load_plugins=False,
                                        load_receipt=False)]
            msg = "please specify a cluster"
            if cls:
                opts = ', '.join(cls)
                msg = " ".join([msg, '(options:', opts, ')'])
            self.parser.error(msg)
        for cluster_name in args:
            try:
                cl = self.cm.get_cluster(cluster_name)
            except exception.ClusterDoesNotExist:
                raise
            except Exception, e:
                log.debug("Failed to load cluster settings!", exc_info=True)
                log.error("Failed to load cluster settings!")
                if self.opts.force:
                    log.warn("Ignoring cluster settings due to --force option")
                    cl = self.cm.get_cluster(cluster_name, load_receipt=False,
                                             require_keys=False)
                else:
                    if not isinstance(e, exception.IncompatibleCluster):
                        log.error("Use -f to forcefully stop the cluster")
                    raise
            is_stoppable = cl.is_stoppable()
            if not is_stoppable:
                has_stoppable_nodes = cl.has_stoppable_nodes()
                if not self.opts.terminate_unstoppable and has_stoppable_nodes:
                    raise exception.BaseException(
                        "Cluster '%s' contains 'stoppable' and 'unstoppable' "
                        "nodes. Your options are:\n\n"
                        "1. Use the --terminate-unstoppable option to "
                        "stop all 'stoppable' nodes and terminate all "
                        "'unstoppable' nodes\n\n"
                        "2. Use the 'terminate' command to destroy the "
                        "cluster.\n\nPass --help for more info." %
                        cluster_name)
                if not has_stoppable_nodes:
                    raise exception.BaseException(
                        "Cluster '%s' does not contain any 'stoppable' nodes "
                        "and can only be terminated. Please use the "
                        "'terminate' command instead to destroy the cluster."
                        "\n\nPass --help for more info" % cluster_name)
            if not self.opts.confirm:
                resp = raw_input("Stop cluster %s (y/n)? " % cluster_name)
                if resp not in ['y', 'Y', 'yes']:
                    log.info("Aborting...")
                    continue
            cl.stop_cluster(self.opts.terminate_unstoppable,
                            force=self.opts.force)
            log.warn("All non-spot, EBS-backed nodes are now in a "
                     "'stopped' state")
            log.warn("You can restart this cluster by passing -x "
                     "to the 'start' command")
            log.warn("Use the 'terminate' command to *completely* "
                     "terminate this cluster")
