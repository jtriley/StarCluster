#!/usr/bin/env python
import posixpath

from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log


class IPCluster(ClusterSetup):
    """
    Starts an IPCluster on StarCluster
    """

    cluster_file = '/etc/clusterfile.py'
    log_file = '/var/log/ipcluster.log'

    def _create_cluster_file(self, master, nodes):
        engines = {}
        for node in nodes:
            engines[node.alias] = node.num_processors
        cfile = 'send_furl = True\n'
        cfile += 'engines = %s\n' % engines
        f = master.ssh.remote_file(self.cluster_file, 'w')
        f.write(cfile)
        f.close()

    def run(self, nodes, master, user, user_shell, volumes):
        self._create_cluster_file(master, nodes)
        log.info("Starting ipcluster...")
        master.ssh.execute(
            "su - %s -c 'screen -d -m ipcluster ssh --clusterfile %s'" % \
            (user, self.cluster_file))

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Adding %s to ipcluster" % node.alias)
        self._create_cluster_file(master, nodes)
        user_home = node.getpwnam(user).pw_dir
        furl_file = posixpath.join(user_home, '.ipython', 'security',
                                   'ipcontroller-engine.furl')
        node.ssh.execute(
            "su - %s -c 'screen -d -m ipengine --furl-file %s'" % \
            (user, furl_file))

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        log.info("Removing %s from ipcluster" % node.alias)
        less_nodes = filter(lambda x: x.id != node.id, nodes)
        self._create_cluster_file(master, less_nodes)
        node.ssh.execute('pkill ipengine')
