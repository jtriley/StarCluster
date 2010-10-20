#!/usr/bin/env python

from completers import ClusterCompleter


class CmdSshMaster(ClusterCompleter):
    """
    sshmaster [options] <cluster>

    SSH to a cluster's master node

    Example:

        $ sshmaster mycluster
    """
    names = ['sshmaster', 'sm']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        for arg in args:
            self.cm.ssh_to_master(arg, user=self.opts.user)
