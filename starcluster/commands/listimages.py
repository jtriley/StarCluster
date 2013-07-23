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


class CmdListImages(CmdBase):
    """
    listimages [options]

    List all registered EC2 images (AMIs)
    """
    names = ['listimages', 'li']

    def addopts(self, parser):
        parser.add_option(
            "-x", "--executable-by-me", dest="executable",
            action="store_true", default=False,
            help=("Show images owned by other users that " +
                  "you have permission to execute"))

    def execute(self, args):
        if self.opts.executable:
            self.ec2.list_executable_images()
        else:
            self.ec2.list_registered_images()
