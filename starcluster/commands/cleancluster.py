from completers import NodeCompleter


class CmdCleanCluster(NodeCompleter):
    """
    datacratic_update

    Calls the grid plugins to allow them to clean their master host.
    Usefull with a spot instances cluster.
    """
    names = ['cleancluster']

    def addopts(self, parser):
        pass

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = self.tag = args[0]
        cluster = self.cm.get_cluster(tag)
        cluster.clean()
