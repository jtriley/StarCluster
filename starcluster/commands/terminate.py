#!/usr/bin/env python

from starcluster.logger import log

from completers import ClusterCompleter


class CmdTerminate(ClusterCompleter):
    """
    terminate [options] <cluster_tag> ...

    Terminate a running or stopped cluster

    Example:

        $ starcluster terminate mycluster

    This will terminate a currently running or stopped cluster tagged
    "mycluster". All instances will be terminated and the cluster's
    security group will be removed. In the case of EBS-backed instances,
    the instance's root volume will also be deleted.
    """
    names = ['terminate']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="Do not prompt for confirmation, " + \
                          "just terminate the cluster")

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        for cluster_name in args:
            cl = self.cm.get_cluster(cluster_name)
            if not self.opts.confirm:
                action = 'Terminate'
                if cl.is_ebs_cluster():
                    action = 'Terminate EBS'
                resp = raw_input(
                    "%s cluster %s (y/n)? " % (action, cluster_name))
                if resp not in ['y', 'Y', 'yes']:
                    log.info("Aborting...")
                    continue
            cl.terminate_cluster()
