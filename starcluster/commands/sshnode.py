#!/usr/bin/env python

from completers import NodeCompleter


class CmdSshNode(NodeCompleter):
    """
    sshnode <cluster> <node>

    SSH to a cluster node

    Examples:

        $ starcluster sshnode mycluster master
        $ starcluster sshnode mycluster node001
        ...

    or same thing in shorthand:

        $ starcluster sshnode mycluster 0
        $ starcluster sshnode mycluster 1
        ...
    """
    names = ['sshnode', 'sn']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                "please specify a <cluster> and <node> to connect to")
        scluster = args[0]
        ids = args[1:]
        for id in ids:
            self.cm.ssh_to_cluster_node(scluster, id, user=self.opts.user)
