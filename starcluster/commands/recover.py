from completers import NodeCompleter


class CmdRecover(NodeCompleter):
    """
    recover [--remove] <cluster-tag>

    Calls recover_nodes on each plugins. For OGS, missing active nodes are put
    back in.

    Putting a node back in is the equivalent of running
    addnode -x -a <node-alias> <cluster-tag>.
    """

    names = ['recover']

    def addopts(self, parser):
        parser.add_option("--remove",
                          dest="remove", default=False,
                          help="If recover fails, remove the node if "
                               "has passed <remove> minutes within the "
                               "hour block.")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = args[0]

        cluster = self.cm.get_cluster(tag)
        cluster.recover(self.opts.remove)
