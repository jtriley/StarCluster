# Copyright 2009-2013 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import clustersetup
from starcluster.logger import log


class XvfbSetup(clustersetup.DefaultClusterSetup):
    """
    Installs, configures, and sets up an Xvfb server
    (thanks to Adam Marsh for his contribution)
    """
    def _install_xvfb(self, node):
        node.apt_install('xvfb')

    def _launch_xvfb(self, node):
        node.ssh.execute('screen -d -m Xvfb :1 -screen 0 1024x768x16')
        profile = node.ssh.remote_file('/etc/profile.d/scxvfb.sh', 'w')
        profile.write('export DISPLAY=":1"')
        profile.close()

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Installing Xvfb on all nodes")
        for node in nodes:
            self.pool.simple_job(self._install_xvfb, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Launching Xvfb Server on all nodes")
        for node in nodes:
            self.pool.simple_job(self._launch_xvfb, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def _terminate(self, nodes):
        for node in nodes:
            self.pool.simple_job(node.ssh.execute, ('pkill Xvfb'),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def on_add_node(self, new_node, nodes, master, user, user_shell, volumes):
        log.info("Installing Xvfb on %s" % new_node.alias)
        self._install_xvfb(new_node)
        log.info("Launching Xvfb Server on %s" % new_node.alias)
        self._launch_xvfb(new_node)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError('on_remove_node method not implemented')
