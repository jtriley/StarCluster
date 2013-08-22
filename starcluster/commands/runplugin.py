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
