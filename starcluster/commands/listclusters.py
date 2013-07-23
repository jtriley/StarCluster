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


class CmdListClusters(ClusterCompleter):
    """
    listclusters [<cluster_tag> ...]

    List all active clusters
    """
    names = ['listclusters', 'lc']

    def addopts(self, parser):
        parser.add_option("-s", "--show-ssh-status", dest="show_ssh_status",
                          action="store_true", default=False,
                          help="output whether SSH is up on each node or not")

    def execute(self, args):
        self.cm.list_clusters(cluster_groups=args,
                              show_ssh_status=self.opts.show_ssh_status)
