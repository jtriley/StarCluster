#!/usr/bin/env python

import time

from starcluster import exception
from starcluster.logger import log

from completers import InstanceCompleter


class CmdCreateImage(InstanceCompleter):
    """
    createimage [options] <instance-id> <image_name> <bucket>

    Create a new instance-store image (AMI) from a running EC2 instance

    Example:

        $ starcluster createimage i-999999 my-new-image mybucket

    NOTE: It is recommended not to create a new StarCluster AMI from
    an instance launched by StarCluster. Rather, launch a single
    StarCluster instance using ElasticFox or the EC2 API tools, modify
    it to your liking, and then use this command to create a new AMI from
    the running instance.
    """
    names = ['createimage', 'ci']
    show_dns_names = True

    bucket = None
    image_name = None

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
            help="short description for new EBS snapshot (for EBS AMIs)")
        parser.add_option(
            "-e", "--ebs", dest="create_ebs_image", action="store_true",
            default=False, help="create an EBS-backed AMI")
        parser.add_option(
            "-s", "--s3", dest="create_s3_image", action="store_true",
            default=False, help="create an instance-store (S3) AMI")
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
            help="Remove generated image files on the " + \
            "instance after registering (for S3 AMIs)")

    def cancel_command(self, signum, frame):
        raise exception.CancelledCreateImage(self.bucket, self.image_name)

    def execute(self, args):
        if len(args) != 3:
            self.parser.error(
                'you must specify an instance-id, image name, and bucket')
        if self.opts.create_ebs_image and self.opts.create_s3_image:
            self.parser.error(
                'options --ebs and --s3 are mutually exclusive')
        instanceid, image_name, bucket = args
        self.bucket = bucket
        self.image_name = image_name
        i = self.ec2.get_instance(instanceid)
        is_ebs_backed = (i.root_device_type == "ebs")
        key_location = self.cfg.get_key(i.key_name).get('key_location')
        aws_user_id = self.cfg.aws.get('aws_user_id')
        ec2_cert = self.cfg.aws.get('ec2_cert')
        ec2_private_key = self.cfg.aws.get('ec2_private_key')
        create_ebs = self.opts.create_ebs_image or \
                (not self.opts.create_s3_image and is_ebs_backed)
        create_s3 = self.opts.create_s3_image or \
                (not self.opts.create_ebs_image and not is_ebs_backed)
        self.catch_ctrl_c()
        if create_ebs:
            ami_id = self.ec2.create_ebs_image(instanceid, key_location,
                                               image_name,
                                               **self.specified_options_dict)
        elif create_s3:
            ami_id = self.ec2.create_s3_image(instanceid, key_location,
                                              aws_user_id, ec2_cert,
                                              ec2_private_key, bucket,
                                              image_name=image_name,
                                              **self.specified_options_dict)
        log.info("Your new AMI id is: %s" % ami_id)
