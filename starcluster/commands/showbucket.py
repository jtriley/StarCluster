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


class CmdShowBucket(CmdBase):
    """
    showbucket <bucket>

    Show all files in an S3 bucket

    Example:

        $ starcluster showbucket mybucket
    """
    names = ['showbucket', 'sb']

    def execute(self, args):
        if not args:
            self.parser.error('please specify an S3 bucket')
        for arg in args:
            self.s3.list_bucket(arg)
