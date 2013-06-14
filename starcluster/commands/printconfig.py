from completers import NodeCompleter


class CmdPrintConfig(NodeCompleter):
    """
    printconfig <cluster-tag>

    Print the config as stored within the security_group description
    """
    names = ['printconfig', 'pc']

    def addopts(self, parser):
        pass

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = self.tag = args[0]
        cluster = self.cm.get_cluster(tag)
        cluster.print_config()

        plugins_metadata = cluster.master_node.get_plugins_full_metadata(
            cluster.plugins_order)
        for klass, args, kwargs in plugins_metadata:
            print str(klass), "-", str(args), "-", str(kwargs)
