#!/usr/bin/env python

from base import CmdBase

class CmdListImages(CmdBase):
    """
    listimages [options]

    List all registered EC2 images (AMIs)
    """
    names = ['listimages', 'li']

    def addopts(self, parser):
        opt = parser.add_option(
            "-x","--executable-by-me", dest="executable",
            action="store_true", default=False,
            help="Show images that you have permission to execute")

    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        if self.opts.executable:
            ec2.list_executable_images()
        else:
            ec2.list_registered_images()
