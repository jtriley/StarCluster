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


class CmdListInstances(CmdBase):
    """
    listinstances [options]

    List all running EC2 instances
    """
    names = ['listinstances', 'lsi']

    def addopts(self, parser):
        parser.add_option("-t", "--show-terminated", dest="show_terminated",
                          action="store_true", default=False,
                          help="show terminated instances")

    def execute(self, args):
        self.ec2.list_all_instances(self.opts.show_terminated)
