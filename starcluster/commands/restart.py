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

from completers import ClusterCompleter


class CmdRestart(ClusterCompleter):
    """
    restart [options] <cluster_tag>

    Restart an existing cluster

    Example:

        $ starcluster restart mynewcluster

    This command will reboot each node (without terminating), wait for the
    nodes to come back up, and then reconfigures the cluster without losing
    any data on the node's local disk
    """
    names = ['restart', 'reboot']

    def addopts(self, parser):
        parser.add_option("-o", "--reboot-only", dest="reboot_only",
                          action="store_true", default=False,
                          help="only reboot EC2 instances (skip plugins)")

    tag = None

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster <tag_name>")
        for arg in args:
            self.cm.restart_cluster(arg, reboot_only=self.opts.reboot_only)
