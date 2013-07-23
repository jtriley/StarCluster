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

from starcluster.logger import log

from completers import S3ImageCompleter


class CmdDownloadImage(S3ImageCompleter):
    """
    downloadimage [options] <image_id> <destination_directory>

    Download the manifest.xml and all AMI parts for an instance-store AMI

    Example:

        $ starcluster downloadimage ami-asdfasdf /data/myamis/ami-asdfasdf
    """
    names = ['downloadimage', 'di']

    bucket = None
    image_name = None

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                'you must specify an <image_id> and <destination_directory>')
        image_id, destdir = args
        self.ec2.download_image_files(image_id, destdir)
        log.info("Finished downloading AMI: %s" % image_id)
