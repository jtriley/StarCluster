#!/usr/bin/env python

from completers import ClusterCompleter


class CmdRemoveNode(ClusterCompleter):
    """
    removenode [options] <cluster_tag> <node> [<node> ...]

    Terminate one or more nodes in the cluster

    Example:

        $ starcluster removenode mynewcluster node003

    This will remove node003 from mynewcluster and terminate the node.
    """
    names = ['removenode', 'rn']

    tag = None

    def addopts(self, parser):
        parser.add_option("-k", "--keep-instance", dest="terminate",
                          action="store_false", default=True,
                          help="do not terminate instances "
                          "after removing nodes")

    def execute(self, args):
        if not len(args) >= 2:
            self.parser.error("please specify a <cluster_tag> and <node>")
        tag = self.tag = args[0]
        aliases = args[1:]
        for alias in aliases:
            self.cm.remove_node(tag, alias, terminate=self.opts.terminate)
