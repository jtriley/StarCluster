# Copyright 2017 Daniel Treiman
#

import os
from starcluster import clustersetup
from starcluster.logger import log


class JupyterhubPlugin(clustersetup.DefaultClusterSetup):

    def _add_jupyterhub_node(self, node):
        node.ssh.execute('sudo mkdir -p /run/user/1001/jupyter && sudo chmod -R ugo+rwx /run/user/1001')

    def _setup_jupyterhub(self, master=None, nodes=None):
        log.info('Setting up Jupyterhub environment')
        master = master or self._master
        nodes = nodes or self.nodes
        log.info('Starting Jupyterhub server')
        self._add_jupyterhub_node(master)
        master.ssh.execute('sudo systemctl start jupyterhub')
        log.info('Configuring Jupyter nodes')
        for node in nodes:
            self.pool.simple_job(self._add_jupyterhub_node, (node,),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        # Start jupyterhub process

    def run(self, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        self._setup_jupyterhub()

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info('Configuring %s for Jupyterhub' % node.alias)
        self._add_jupyterhub_node(node)
