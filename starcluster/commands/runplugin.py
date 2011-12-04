from base import CmdBase


class CmdRunPlugin(CmdBase):
    """
    runplugin <plugin_name> <cluster_tag>

    Run a StarCluster plugin on a running cluster

    plugin_name - name of plugin section defined in the config
    cluster_tag - tag name of a running StarCluster

    Example:

       $ starcluster runplugin myplugin mycluster
    """
    names = ['runplugin', 'rp']

    def execute(self, args):
        if len(args) != 2:
            self.parser.error("Please provide a plugin_name and <cluster_tag>")
        plugin_name, cluster_tag = args
        self.cm.run_plugin(plugin_name, cluster_tag)
