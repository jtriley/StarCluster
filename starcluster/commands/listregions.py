from base import CmdBase


class CmdListRegions(CmdBase):
    """
    listregions

    List all EC2 regions
    """
    names = ['listregions', 'lr']

    def execute(self, args):
        self.ec2.list_regions()
