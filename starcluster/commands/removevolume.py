from starcluster.logger import log

from completers import VolumeCompleter


class CmdRemoveVolume(VolumeCompleter):
    """
    removevolume [options] <volume_id>

    Delete one or more EBS volumes

    WARNING: This command will *PERMANENTLY* remove an EBS volume.
    Please use caution!

    Example:

        $ starcluster removevolume vol-999999
    """
    names = ['removevolume', 'rv']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, just "
                          "remove the volume")

    def execute(self, args):
        if not args:
            self.parser.error("no volumes specified. exiting...")
        for arg in args:
            volid = arg
            vol = self.ec2.get_volume(volid)
            if vol.status in ['attaching', 'in-use']:
                log.error("volume is currently in use. aborting...")
                return
            if vol.status == 'detaching':
                log.error("volume is currently detaching. "
                          "please wait a few moments and try again...")
                return
            if not self.opts.confirm:
                resp = raw_input("**PERMANENTLY** delete %s (y/n)? " % volid)
                if resp not in ['y', 'Y', 'yes']:
                    log.info("Aborting...")
                    return
            if vol.delete():
                log.info("Volume %s deleted successfully" % vol.id)
            else:
                log.error("Error deleting volume %s" % vol.id)
