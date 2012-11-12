import traceback
import re
from starcluster import clustersetup
from starcluster.templates import sge
from starcluster.logger import log


class DatacraticPlugin(clustersetup.DefaultClusterSetup):

    def __init__(self, **kwargs):
        pass
    
    def run(self, nodes, master, user, user_shell, volumes):
        self._master = master
        log.info("Datacratic plugin: setting master to 0 slot")
        self._set_node_slots("master", 0)
        pass

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._master = master
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

        log.info("Overriding SGE node config to set slots=1")
        self._set_node_slots(node.alias, 1)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        pass

    def clean_cluster(self, nodes, master, user, user_shell, volumes):
        pass


    def _set_node_slots(self, node_alias, num_slots):
        master = self._master
        dcePath = "/usr/bin/datacraticCopyEditor"
        qconfPath = "/root/queueconfig.qconf"
        if not master.ssh.path_exists(dcePath):
            #TODO: nice hack, complete it by doing the entire stuff remotely
            dce = master.ssh.remote_file(dcePath, "w")
            dce.write("#!/bin/bash\ncp $1 " + qconfPath + "\n")
            dce.close()
        #with our copy editor, the current config is printed to a file
        master.ssh.execute("export EDITOR=" + dcePath + "; "\
            + "chmod +x $EDITOR; "\
            + "echo $EDITOR; "\
            + "qconf -mq all.q", source_profile=True)
        qconf = master.ssh.remote_file(qconfPath, "r")
        qconfStr = qconf.read()
        qconf.close()
        search = "\[" + node_alias + "=[\d]+\]"
        replace = "[" + node_alias + "=" + str(num_slots) + "]"
        qconfStr, numReplace = re.subn(search, replace, qconfStr)
        if numReplace == 0:
            log.error("datacratic plugin: failed to set " + str(num_slots) +\
                " slot(s) on node " + node_alias)
        else:
            qconf = master.ssh.remote_file(qconfPath, "w")
            qconf.write(qconfStr)
            qconf.close()
            master.ssh.execute("qconf -Mq " + qconfPath, 
                source_profile=True)

