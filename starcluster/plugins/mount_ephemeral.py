import os
from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log
 
class MountEphemeralPlugin(ClusterSetup):
    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Mount ephemeral storage on all nodes as /tmp/ephemeralXXX...")
        plugin_dir = os.path.dirname(os.path.realpath(__file__))
	for node in nodes:
            log.info("Configuring ephemeral storage for %s" % node.alias)

            #volumes = node.get_volumes()
            #print "Volumes: "
            #print (volumes)
            #print ""

            #device_map = node.get_device_map()
            #print "Device Map: "
            #print(device_map)
            #print ""

            node.ssh.put(plugin_dir + "/mount_ephemeral.sh", ".")
            node.ssh.execute("sh ./mount_ephemeral.sh")

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Mounting ephemeral storage on %s" % node.alias)
