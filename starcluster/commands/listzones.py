from base import CmdBase


class CmdListZones(CmdBase):
    """
    listzones

    List all EC2 availability zones in the current region (default: us-east-1)
    """
    names = ['listzones', 'lz']

    def addopts(self, parser):
        parser.add_option("-r", "--region", dest="region", default=None,
                          help="Show all zones in a given region "
                          "(see listregions)")

    def execute(self, args):
        self.ec2.list_zones(region=self.opts.region)
