from starcluster.logger import log

from completers import ImageCompleter


class CmdRemoveImage(ImageCompleter):
    """
    removeimage [options] <imageid>

    Deregister an EC2 image (AMI)

    WARNING: This command, by default, will *permanently* remove an AMI from
    EC2. This includes removing any AMI files in the S3-backed case and the
    root volume snapshot in the EBS-backed case. Be careful!

    Example:

        $ starcluster removeimage ami-999999

    If the image is S3-backed then the image files on S3 will be removed in
    addition to deregistering the AMI.

    If the image is EBS-backed then the image's snapshot on EBS will be removed
    in addition to deregistering the AMI.

    If you'd rather keep the S3 files/EBS Snapshot backing the image use the
    --keep-image-data:

        $ starcluster removeimage -k ami-999999

    For S3-backed images this will leave the AMI's files on S3 instead of
    deleting them. For EBS-backed images this will leave the root volume
    snapshot on EBS instead of deleting it.
    """
    names = ['removeimage', 'ri']

    def addopts(self, parser):
        parser.add_option("-p", "--pretend", dest="pretend",
                          action="store_true", default=False,
                          help="pretend run, do not actually remove anything")
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, "
                          "just remove the image")
        parser.add_option("-k", "--keep-image-data", dest="keep_image_data",
                          action="store_true", default=False,
                          help="only deregister the AMI, do not remove files "
                          "from S3 or delete EBS snapshot")

    def execute(self, args):
        if not args:
            self.parser.error("no images specified. exiting...")
        for arg in args:
            imageid = arg
            self.ec2.get_image(imageid)
            confirmed = self.opts.confirm
            pretend = self.opts.pretend
            keep_image_data = self.opts.keep_image_data
            if not confirmed:
                if not pretend:
                    resp = raw_input("**PERMANENTLY** delete %s (y/n)? " %
                                     imageid)
                    if resp not in ['y', 'Y', 'yes']:
                        log.info("Aborting...")
                        return
            self.ec2.remove_image(imageid, pretend=pretend,
                                  keep_image_data=keep_image_data)
