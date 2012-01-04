from base import CmdBase


class CmdListPublic(CmdBase):
    """
    listpublic

    List all public StarCluster images on EC2
    """
    names = ['listpublic', 'lp']

    def execute(self, args):
        self.ec2.list_starcluster_public_images()
