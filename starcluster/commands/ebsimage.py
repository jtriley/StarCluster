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

import time

from starcluster import exception
from starcluster.logger import log

from completers import InstanceCompleter


class CmdEbsImage(InstanceCompleter):
    """
    ebsimage [options] <instance-id> <image_name>

    Create a new EBS image (AMI) from a running EC2 instance

    Example:

        $ starcluster ebsimage i-999999 my-new-image-ebs

    NOTE: It should now be safe to create an image from an instance launched by
    StarCluster. If you have issues please submit a bug report to the mailing
    list.
    """
    names = ['ebsimage', 'eimg']

    def addopts(self, parser):
        parser.add_option(
            "-d", "--description", dest="description", action="store",
            type="string",
            default="Image created @ %s" % time.strftime("%Y%m%d%H%M"),
            help="short description of this AMI")
        parser.add_option(
            "-D", "--snapshot-description", dest="snapshot_description",
            action="store", type="string",
            default="Snapshot created @ %s" % time.strftime("%Y%m%d%H%M"),
            help="short description for new EBS snapshot")
        parser.add_option(
            "-k", "--kernel-id", dest="kernel_id", action="store",
            type="string", default=None,
            help="kernel id for the new AMI")
        parser.add_option(
            "-r", "--ramdisk-id", dest="ramdisk_id", action="store",
            type="string", default=None,
            help="ramdisk id for the new AMI")
        parser.add_option(
            "-s", "--root-volume-size", dest="root_vol_size", type="int",
            action="callback", default=15, callback=self._positive_int,
            help="size of root volume (only used when creating an "
            "EBS image from an S3 instance)")

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                'you must specify an instance-id and image name')
        instanceid, image_name = args
        i = self.ec2.get_instance(instanceid)
        is_ebs_backed = (i.root_device_type == "ebs")
        key_location = self.cfg.get_key(i.key_name).get('key_location')
        try:
            ami_id = self.ec2.create_ebs_image(instanceid, key_location,
                                               image_name,
                                               **self.specified_options_dict)
            log.info("Your new AMI id is: %s" % ami_id)
        except KeyboardInterrupt:
            raise exception.CancelledEBSImageCreation(image_name,
                                                      is_ebs_backed)
