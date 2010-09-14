#!/usr/bin/env python

import sys
import time

from starcluster import image
from starcluster import config
from starcluster import static
from starcluster import exception
from starcluster import optcomplete
from starcluster.logger import log

from base import CmdBase

class CmdCreateImage(CmdBase):
    """
    createimage [options] <instance-id> <image_name> <bucket>

    Create a new instance-store image (AMI) from a currently running EC2 instance

    Example:

        $ starcluster createimage i-999999 my-new-image mybucket

    NOTE: It is recommended not to create a new StarCluster AMI from
    an instance launched by StarCluster. Rather, launch a single
    StarCluster instance using ElasticFox or the EC2 API tools, modify
    it to your liking, and then use this command to create a new AMI from
    the running instance.
    """
    names = ['createimage', 'ci']

    bucket = None
    image_name = None

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig().load()
                ec2 = cfg.get_easy_ec2()
                instances = ec2.get_all_instances()
                completion_list = [i.id for i in instances]
                completion_list.extend([i.dns_name for i in instances])
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def addopts(self, parser):
        opt = parser.add_option(
            "-c","--confirm", dest="confirm",
            action="store_true", default=False,
            help="Do not warn about re-imaging StarCluster instances")
        opt = parser.add_option(
            "-r","--remove-image-files", dest="remove_image_files",
            action="store_true", default=False,
            help="Remove generated image files on the instance after registering")
        opt = parser.add_option(
            "-d","--description", dest="description", action="store",
            type="string", default=time.strftime("%Y%m%d%H%M"),
            help="short description of this AMI")
        opt = parser.add_option(
            "-k","--kernel-id", dest="kernel_id", action="store",
            type="string", default=None,
            help="kernel id for the new AMI")
        opt = parser.add_option(
            "-R","--ramdisk-id", dest="ramdisk_id", action="store",
            type="string", default=None,
            help="ramdisk id for the new AMI")

    def cancel_command(self, signum, frame):
        raise exception.CancelledCreateImage(self.bucket, self.image_name)

    def execute(self, args):
        if len(args) != 3:
            self.parser.error('you must specify an instance-id, image name, and bucket')
        instanceid, image_name, bucket = args
        self.bucket = bucket
        self.image_name = image_name
        cfg = self.cfg
        ec2 = cfg.get_easy_ec2()
        i = ec2.get_instance(instanceid)
        if not self.opts.confirm:
            for group in i.groups:
                if group.id.startswith(static.SECURITY_GROUP_PREFIX):
                    log.warn("Instance %s is a StarCluster instance" % i.id)
                    print
                    log.warn("Creating an image from a StarCluster instance " + \
                    "can lead to problems when attempting to use the resulting " + \
                    "image with StarCluster later on")
                    print
                    log.warn(
                    "The recommended way to re-image a StarCluster AMI is " + \
                    "to launch a single instance using either ElasticFox, the " +\
                    "EC2 command line tools, or the AWS management console. " +\
                    "Then login to the instance, modify it, and use this " + \
                    "command to create a new AMI from it.")
                    print
                    resp = raw_input("Continue anyway (y/n)? ")
                    if resp not in ['y','Y','yes']:
                        log.info("Aborting...")
                        sys.exit(1)
                    break
        self.catch_ctrl_c()
        ami_id = image.create_image(instanceid, image_name, bucket, cfg,
                           **self.specified_options_dict)
        log.info("Your new AMI id is: %s" % ami_id)
