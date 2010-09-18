#!/usr/bin/env python

from starcluster import config
from starcluster import cluster
from starcluster import optcomplete
from starcluster.logger import log

from base import CmdBase


class CmdSshMaster(CmdBase):
    """
    sshmaster [options] <cluster>

    SSH to a cluster's master node

    Example:

        $ sshmaster mycluster
    """
    names = ['sshmaster', 'sm']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig().load()
                clusters = cluster.get_cluster_security_groups(cfg)
                completion_list = [cluster.get_tag_from_sg(sg.name) \
                                   for sg in clusters]
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="USER", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        for arg in args:
            cluster.ssh_to_master(arg, self.cfg, user=self.opts.USER)
