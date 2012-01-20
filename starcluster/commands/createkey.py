from starcluster.logger import log

from base import CmdBase


class CmdCreateKey(CmdBase):
    """
    createkey [options] <name>

    Create a new Amazon EC2 keypair
    """
    names = ['createkey', 'ck']

    def addopts(self, parser):
        parser.add_option("-o", "--output-file", dest="output_file",
                          action="store", type="string", default=None,
                          help="Save the new keypair to a file")
        #parser.add_option("-a","--add-to-config", dest="add_to_config",
            #action="store_true", default=False,
            #help="add new keypair to StarCluster config")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please provide a key name")
        name = args[0]
        ofile = self.opts.output_file
        kp = self.ec2.create_keypair(name, output_file=ofile)
        log.info("Successfully created keypair: %s" % name)
        log.info("fingerprint: %s" % kp.fingerprint)
        log.info("contents: \n%s" % kp.material)
        if ofile:
            log.info("keypair written to %s" % ofile)
