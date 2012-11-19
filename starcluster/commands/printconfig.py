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
        self.cm.get_cluster(tag).print_config()
