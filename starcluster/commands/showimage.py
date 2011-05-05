#!/usr/bin/env python

#from base import CmdBase
from downloadimage import CmdDownloadImage


class CmdShowImage(CmdDownloadImage):
    """
    showimage <image_id>

    Show all AMI parts and manifest files on S3 for an instance-store AMI

    Example:

        $ starcluster showimage ami-999999
    """
    names = ['showimage', 'shimg']

    def execute(self, args):
        if not args:
            self.parser.error('please specify an AMI id')
        for arg in args:
            self.ec2.list_image_files(arg)
