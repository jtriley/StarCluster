import sys
import time
import warnings

from starcluster import exception
from starcluster.logger import log

from completers import InstanceCompleter


class CmdS3Image(InstanceCompleter):
    """
    s3image [options] <instance-id> <image_name> [<bucket>]

    Create a new instance-store (S3) AMI from a running EC2 instance

    Example:

        $ starcluster s3image i-999999 my-new-image mybucket

    NOTE: It should now be safe to create an image from an instance launched by
    StarCluster. If you have issues please submit a bug report to the mailing
    list.
    """
    names = ['s3image', 'simg', 'createimage']

    bucket = None
    image_name = None

    def addopts(self, parser):
        parser.add_option(
            "-d", "--description", dest="description", action="store",
            type="string",
            default="Image created @ %s" % time.strftime("%Y%m%d%H%M"),
            help="short description of this AMI")
        parser.add_option(
            "-k", "--kernel-id", dest="kernel_id", action="store",
            type="string", default=None,
            help="kernel id for the new AMI")
        parser.add_option(
            "-R", "--ramdisk-id", dest="ramdisk_id", action="store",
            type="string", default=None,
            help="ramdisk id for the new AMI")
        parser.add_option(
            "-r", "--remove-image-files", dest="remove_image_files",
            action="store_true", default=False,
            help="Remove generated image files on the "
            "instance after registering (for S3 AMIs)")

    def cancel_command(self, signum, frame):
        raise exception.CancelledS3ImageCreation(self.bucket, self.image_name)

    def execute(self, args):
        if "createimage" in sys.argv:
            warnings.warn("createimage is deprecated and will go away in the "
                          "next release. please use the s3image/ebsimage "
                          "commands instead", DeprecationWarning)
        if len(args) != 3:
            self.parser.error(
                'you must specify an instance-id, image name, and bucket')
        bucket = None
        instanceid, image_name, bucket = args
        self.bucket = bucket
        self.image_name = image_name
        i = self.ec2.get_instance(instanceid)
        key_location = self.cfg.get_key(i.key_name).get('key_location')
        aws_user_id = self.cfg.aws.get('aws_user_id')
        ec2_cert = self.cfg.aws.get('ec2_cert')
        ec2_private_key = self.cfg.aws.get('ec2_private_key')
        self.catch_ctrl_c()
        ami_id = self.ec2.create_s3_image(instanceid, key_location,
                                          aws_user_id, ec2_cert,
                                          ec2_private_key, bucket,
                                          image_name=image_name,
                                          **self.specified_options_dict)
        log.info("Your new AMI id is: %s" % ami_id)
