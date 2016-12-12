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

from starcluster import static

from base import CmdBase


class CmdListSnapshots(CmdBase):
    """
    listsnapshots

    List all EBS snapshots
    """
    names = ['listsnapshots', 'lsn']

    def addopts(self, parser):
        parser.add_option("-n", "--name", dest="name", type="string",
                          default=None, action="store",
                          help="show all snapshots with a given 'Name' tag")
        parser.add_option("-S", "--status", dest="status", action="store",
                          default=None, choices=static.SNAPSHOT_STATUS,
                          help="show all snapshots with status")
        parser.add_option("-i", "--snapshot-id", dest="snapshot_id",
                          action="store", type="string", default=None,
                          help="show all snapshots with id")
        parser.add_option("-o", "--owner", dest="owner",
                          action="store", type="string", default="self",
                          help=("show all snapshots with owner "
                                "(e.g. 'self' [default], 'amazon', or an aws id)"))
        parser.add_option("-v", "--volume-id", dest="volume_id",
                          action="store", type="string", default=None,
                          help="show all snapshots created from volume")
        parser.add_option("-t", "--tag", dest="tags", type="string",
                          default={}, action="callback",
                          callback=self._build_dict,
                          help="show all snapshots with a given tag")

    def execute(self, args):
        self.ec2.list_snapshots(**self.options_dict)
