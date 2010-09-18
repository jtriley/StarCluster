#!/usr/bin/env python

from starcluster import config
from starcluster import optcomplete
from starcluster.logger import log

from base import CmdBase


class CmdDownloadImage(CmdBase):
    """
    downloadimage [options] <image_id> <destination_directory>

    Download the manifest.xml and all AMI parts for an instance-store AMI

    Example:

        $ starcluster downloadimage ami-asdfasdf /data/myamis/ami-asdfasdf
    """
    names = ['downloadimage', 'di']

    bucket = None
    image_name = None

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig().load()
                ec2 = cfg.get_easy_ec2()
                rimages = ec2.registered_images
                completion_list = [i.id for i in rimages]
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                'you must specify an <image_id> and <destination_directory>')
        image_id, destdir = args
        ec2 = self.cfg.get_easy_ec2()
        ec2.download_image_files(image_id, destdir)
        log.info("Finished downloading AMI: %s" % image_id)
