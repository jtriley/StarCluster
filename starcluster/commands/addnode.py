#!/usr/bin/env python

from completers import ClusterCompleter


class CmdAddNode(ClusterCompleter):
    """
    addnode [options] <cluster_tag>

    Add a node to a running cluster

    Example:

        $ starcluster addnode mynewcluster

    This will add a new node to mynewcluster. To give the node an alias:

        $ starcluster addnode -a mynode mynewcluster
    """
    names = ['addnode', 'an']

    tag = None

    def addopts(self, parser):
        parser.add_option("-a", "--alias", dest="alias",
                          action="store", type="string", default=None,
                          help=("alias to give to the new node " + \
                                "(e.g. node007, mynode, etc)"))

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = self.tag = args[0]
        aliases = None
        if self.opts.alias:
            aliases = [self.opts.alias]
        self.cm.add_node(tag, aliases)
