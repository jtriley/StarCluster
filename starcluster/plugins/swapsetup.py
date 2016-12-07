# Copyright 2009-2014 Justin Riley
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

"""
"""
from starcluster.clustersetup import DefaultClusterSetup
from starcluster.logger import log
from starcluster.utils import print_timing


class SwapSetup(DefaultClusterSetup):
    """Setup swap space"""

    def __init__(self, swap_file="/swapfile", amount=None):
        super(SwapSetup, self).__init__()
        self.swap_file = swap_file
        self.amount = amount and amount.strip()

    @print_timing("SwapSetup")
    def setup_swap(self, nodes):
        if not self.amount:
            log.info("No amount specified!")
            return

        log.info("Setting up swap")

        commands = []
        commands.append('fallocate -l %s %s' % (self.amount, self.swap_file))
        commands.append('chmod 600 %s' % self.swap_file)
        commands.append('mkswap %s' % self.swap_file)
        commands.append('swapon %s' % self.swap_file)
        commands.append('swapon -s')

        for command in commands:
            log.info("$ " + command)
        cmd = "\n".join(commands)
        for node in nodes:
            self.pool.simple_job(node.ssh.execute, (cmd,), jobid=node.alias)
        self.pool.wait(len(nodes))

    def run(self, nodes, master, user, user_shell, volumes):
        self.setup_swap(nodes)

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self.setup_swap([node])

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")
