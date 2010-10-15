#!/usr/bin/env python

from starcluster import config
from starcluster import cluster
from starcluster import optcomplete
from starcluster.logger import log

from base import CmdBase


class CmdStop(CmdBase):
    """
    stop [options] <cluster_tag> ...

    Stop a running cluster

    Example:

        $ starcluster stop mycluster

    This will stop a currently running cluster tagged "mycluster"

    If the cluster uses EBS-backed instances, all instances will be put into
    a stopped state. You can then use the start command to resume the cluster
    later on without losing data.

    If the cluster uses instance-store instances then all instances wil be
    terminated and the cluster's security group will be removed. This command
    has the same behaviour as the 'terminate' command in the case of
    instance-store instances.
    """
    names = ['stop']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig().load()
                ec2 = cfg.get_easy_ec2()
                cm = cluster.ClusterManager(cfg, ec2)
                clusters = cm.get_cluster_security_groups()
                completion_list = [cm.get_tag_from_sg(sg.name) \
                                   for sg in clusters]
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

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
