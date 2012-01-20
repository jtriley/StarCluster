from completers import ClusterCompleter


class CmdRemoveNode(ClusterCompleter):
    """
    removenode [options] <cluster_tag> <node> [<node> ...]

    Terminate one or more nodes in the cluster

    Examples:

        $ starcluster removenode mycluster node003

    This will remove node003 from mycluster and terminate the node.

    You can also specify multiple nodes to remove and terminate one after
    another:

        $ starcluster removenode mycluster node001 node002 node003

    If you'd rather not terminate the node(s) after removing from the cluster,
    use the -k option:

        $ starcluster removenode -k mycluster node001 node002 node003

    This will remove the nodes from the cluster but leave the instances
    running. This can be useful, for example, when testing on_add_node methods
    in a StarCluster plugin.
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
