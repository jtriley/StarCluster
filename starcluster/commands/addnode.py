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
        parser.add_option("-x", "--no-create", dest="no_create",
                          action="store_true", default=False,
                          help="do not launch new EC2 instances when " + \
                          "adding nodes (use existing instances instead)")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = self.tag = args[0]
        if not self.opts.alias and self.opts.no_create:
            self.parser.error("you must specify a node alias via the -a "
                              "option when using -x")
        self.cm.add_node(tag, alias=self.opts.alias,
                         no_create=self.opts.no_create)
