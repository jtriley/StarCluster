from starcluster.logger import log

from base import CmdBase


class CmdRemoveKey(CmdBase):
    """
    removekey [options] <name>

    Remove a keypair from Amazon EC2
    """
    names = ['removekey', 'rk']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, just "
                          "remove the keypair")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please provide a key name")
        name = args[0]
        kp = self.ec2.get_keypair(name)
        if not self.opts.confirm:
            resp = raw_input("**PERMANENTLY** delete keypair %s (y/n)? " %
                             name)
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        log.info("Removing keypair: %s" % name)
        kp.delete()
