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
