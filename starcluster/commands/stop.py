#!/usr/bin/env python

from starcluster import config
from starcluster import cluster
from starcluster import optcomplete
from starcluster.logger import log

from base import CmdBase


class CmdStop(CmdBase):
    """
    stop [options] <cluster>

    Shutdown a running cluster

    Example:

        $ starcluster stop mycluster

    This will stop a currently running cluster tagged "mycluster"
    """
    names = ['stop']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig()
                cfg.load()
                clusters = cluster.get_cluster_security_groups(cfg)
                completion_list = [cluster.get_tag_from_sg(sg.name) \
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
        cfg = self.cfg
        for cluster_name in args:
            cl = cluster.get_cluster(cluster_name, cfg)
            if not self.opts.confirm:
                resp = raw_input("Shutdown cluster %s (y/n)? " % cluster_name)
                if resp not in ['y', 'Y', 'yes']:
                    log.info("Aborting...")
                    continue
            cl.stop_cluster()
