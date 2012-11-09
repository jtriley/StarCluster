from completers import NodeCompleter
from starcluster.plugins import sge


class CmdPrintConfig(NodeCompleter):
    """
    printconfig <cluster-tag>

    Print the config as stored within the security_group description
    """
    names = ['pc', 'printconfig']

    def addopts(self, parser):
        pass

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = self.tag = args[0]
        cluster = self.cm.get_cluster(tag).print_config()

