from completers import ClusterCompleter


class CmdListClusters(ClusterCompleter):
    """
    listclusters [<cluster_tag> ...]

    List all active clusters
    """
    names = ['listclusters', 'lc']

    def addopts(self, parser):
        parser.add_option("-s", "--show-ssh-status", dest="show_ssh_status",
                          action="store_true", default=False,
                          help="output whether SSH is up on each node or not")

    def execute(self, args):
        self.cm.list_clusters(cluster_groups=args,
                              show_ssh_status=self.opts.show_ssh_status)
