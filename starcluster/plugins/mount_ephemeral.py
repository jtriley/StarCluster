import os
from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log
 
class MountEphemeralPlugin(ClusterSetup):
    def __init__(self):
        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))

    def mountEphemeralStorage(self, node):
        log.info("Mounting ephemeral storage on %s" % node.alias)
        node.ssh.put(self.plugin_dir + "/mount_ephemeral.sh", ".")
        node.ssh.execute("sh ./mount_ephemeral.sh")

    def run(self, nodes, master, user, user_shell, volumes):
	for node in nodes:
            self.mountEphemeralStorage(node)

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self.mountEphemeralStorage(node)
