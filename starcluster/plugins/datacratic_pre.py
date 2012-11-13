import traceback
import re
from starcluster import clustersetup
from starcluster.templates import sge
from starcluster.logger import log


class DatacraticPrePlugin(clustersetup.DefaultClusterSetup):

    def __init__(self, **kwargs):
        pass
    
    def run(self, nodes, master, user, user_shell, volumes):
        pass

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        #create a 20GB swap in a background process
        log.info("Shutdown order in 3h55 minutes")
        node.ssh.execute_async("shutdown -h +235 StarCluster datacratic plugin "\
            + "sets node auto shutdown in 3h55 minutes.")
        log.info("Creating 20GB swap space on node " + node.alias) 
        node.ssh.execute_async(
            'echo "(/bin/dd if=/dev/zero of=/mnt/20GB.swap bs=1M count=20480; '\
            + '/sbin/mkswap /mnt/20GB.swap; '\
            + '/sbin/swapon /mnt/20GB.swap;) &" > createSwap.sh; '\
            + 'bash createSwap.sh')#TODO: add "rm createSwap.sh"

        log.info("Mounting /opt/sge6 from master")
        node.ssh.execute("sshfs -o allow_other master:/opt/sge6 /opt/sge6")

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        pass

    def clean_cluster(self, nodes, master, user, user_shell, volumes):
        pass
