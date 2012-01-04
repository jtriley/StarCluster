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

    image_name = None
    is_ebs_backed = None

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

    def cancel_command(self, signum, frame):
        raise exception.CancelledEBSImageCreation(self.image_name,
                                                  self.is_ebs_backed)

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                'you must specify an instance-id and image name')
        instanceid, image_name = args
        self.image_name = image_name
        i = self.ec2.get_instance(instanceid)
        self.is_ebs_backed = (i.root_device_type == "ebs")
        key_location = self.cfg.get_key(i.key_name).get('key_location')
        self.catch_ctrl_c()
        ami_id = self.ec2.create_ebs_image(instanceid, key_location,
                                           image_name,
                                           **self.specified_options_dict)
        log.info("Your new AMI id is: %s" % ami_id)
