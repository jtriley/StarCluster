from base import CmdBase


class CmdListSpots(CmdBase):
    """
    listspots

    List all EC2 spot instance requests
    """
    names = ['listspots', 'ls']

    def addopts(self, parser):
        parser.add_option("-c", "--show-closed", dest="show_closed",
                          action="store_true", default=False,
                          help="show closed/cancelled spot instance requests")

    def execute(self, args):
        self.ec2.list_all_spot_instances(self.opts.show_closed)
