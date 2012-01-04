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
            cl = self.cm.get_cluster(cluster_name, require_keys=False)
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
            cl.stop_cluster(self.opts.terminate_unstoppable)
            log.warn("All non-spot, EBS-backed nodes are now in a "
                     "'stopped' state")
            log.warn("You can restart this cluster by passing -x "
                     "to the 'start' command")
            log.warn("Use the 'terminate' command to *completely* "
                     "terminate this cluster")
