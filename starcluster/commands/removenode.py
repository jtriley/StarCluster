#!/usr/bin/env python

from completers import ClusterCompleter


class CmdRemoveNode(ClusterCompleter):
    """
    addnode [options] <cluster_tag> <node>

    Terminate a node in the cluster

    Example:

        $ starcluster removenode mynewcluster node003

    This will remove node003 from mynewcluster and terminate the node.
    """
    names = ['removenode', 'rn']

    tag = None

    def addopts(self, parser):
        pass

    def execute(self, args):
        if len(args) != 2:
            self.parser.error("please specify a <cluster_tag> and <node>")
        tag = self.tag = args[0]
        alias = args[1]
        self.cm.remove_node(tag, alias)
