from completers import ClusterCompleter


class CmdRestart(ClusterCompleter):
    """
    restart [options] <cluster_tag>

    Restart an existing cluster

    Example:

        $ starcluster restart mynewcluster

    This command will reboot each node (without terminating), wait for the
    nodes to come back up, and then reconfigures the cluster without losing
    any data on the node's local disk
    """
    names = ['restart', 'reboot']

    tag = None

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster <tag_name>")
        for arg in args:
            self.cm.restart_cluster(arg)
