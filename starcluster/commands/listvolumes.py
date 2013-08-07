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


class CmdListVolumes(CmdBase):
    """
    listvolumes

    List all EBS volumes
    """
    names = ['listvolumes', 'lv']

    def addopts(self, parser):
        parser.add_option("-n", "--name", dest="name", type="string",
                          default=None, action="store",
                          help="show all volumes with a given 'Name' tag")
        parser.add_option("-d", "--show-deleted", dest="show_deleted",
                          action="store_true", default=False,
                          help="show volumes that are being deleted")
        parser.add_option("-v", "--volume-id", dest="volume_id",
                          action="store", type="string", default=None,
                          help="show a single volume with id VOLUME_ID")
        parser.add_option("-s", "--size", dest="size", action="store",
                          type="string", default=None,
                          help="show all volumes of a particular size")
        parser.add_option("-S", "--status", dest="status", action="store",
                          default=None, choices=static.VOLUME_STATUS,
                          help="show all volumes with status")
        parser.add_option("-a", "--attach-status", dest="attach_status",
                          action="store", default=None,
                          choices=static.VOLUME_ATTACH_STATUS,
                          help="show all volumes with attachment status")
        parser.add_option("-z", "--zone", dest="zone", action="store",
                          type="string", default=None,
                          help="show all volumes in zone")
        parser.add_option("-i", "--snapshot-id", dest="snapshot_id",
                          action="store", type="string", default=None,
                          help="show all volumes created from snapshot")
        parser.add_option("-t", "--tag", dest="tags", type="string",
                          default={}, action="callback",
                          callback=self._build_dict,
                          help="show all volumes with a given tag")

    def execute(self, args):
        self.ec2.list_volumes(**self.options_dict)
