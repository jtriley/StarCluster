#!/usr/bin/env python

from starcluster.logger import log

from completers import ClusterCompleter


class CmdStop(ClusterCompleter):
    """
    stop [options] <cluster_tag> ...

    Stop a running cluster

    Example:

        $ starcluster stop mycluster

    This will stop a currently running cluster tagged "mycluster"

    If the cluster uses EBS-backed instances, all nodes will be put into
    a 'stopped' state preserving the local disks. You can then use the start
    command to resume the cluster later on without losing data.

    If the cluster uses instance-store (S3) instances then all nodes wil be
    terminated and the cluster's security group will be removed. This is the
    same behavior as the 'terminate' command.
    """
    names = ['stop']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="Do not prompt for confirmation, " + \
                          "just shutdown the cluster")

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        for cluster_name in args:
            cl = self.cm.get_cluster(cluster_name)
            is_ebs = cl.is_ebs_cluster()
            if not self.opts.confirm:
                action = "Terminate"
                if is_ebs:
                    action = "Stop EBS"
                    if cl.spot_bid:
                        log.warning("Spot clusters can NOT be stopped, "
                                    "only terminated!")
                        action = "Terminate spot EBS"
                resp = raw_input("%s cluster %s (y/n)? " %
                                 (action, cluster_name))
                if resp not in ['y', 'Y', 'yes']:
                    log.info("Aborting...")
                    continue
            cl.stop_cluster()
            if is_ebs and cl._nodes:
                log.warn(("All EBS-backed nodes in '%s' are now in a " + \
                          "'stopped' state") % cluster_name)
                log.warn("You can restart this cluster by passing -x " + \
                         "to the 'start' command")
                log.warn("Use the 'terminate' command to *completely* " + \
                         "terminate this cluster")
                log.warn("NOTE: Unless EBS-backed nodes are in a " + \
                         "'running' or 'terminated'")
                log.warn("state, you are charged for the EBS volumes " + \
                         "backing the nodes.")
