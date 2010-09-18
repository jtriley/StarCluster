#!/usr/bin/env python

from downloadimage import CmdDownloadImage
from starcluster.logger import log


class CmdRemoveImage(CmdDownloadImage):
    """
    removeami [options] <imageid>

    Deregister an EC2 image (AMI) and remove it from S3

    WARNING: This command *permanently* removes an AMI from
    EC2/S3 including all AMI parts and manifest. Be careful!

    Example:

        $ starcluster removeami ami-999999
    """
    names = ['removeimage', 'ri']

    def addopts(self, parser):
        parser.add_option("-p", "--pretend", dest="pretend",
                          action="store_true", default=False,
                          help="pretend run, dont actually remove anything")
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, just " + \
                          "remove the image")

    def execute(self, args):
        if not args:
            self.parser.error("no images specified. exiting...")
        for arg in args:
            imageid = arg
            ec2 = self.cfg.get_easy_ec2()
            ec2.get_image(imageid)
            confirmed = self.opts.confirm
            pretend = self.opts.pretend
            if not confirmed:
                if not pretend:
                    resp = raw_input("**PERMANENTLY** delete %s (y/n)? " % \
                                     imageid)
                    if resp not in ['y', 'Y', 'yes']:
                        log.info("Aborting...")
                        return
            ec2.remove_image(imageid, pretend=pretend)
