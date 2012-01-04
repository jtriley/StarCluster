from base import CmdBase


class CmdListKeyPairs(CmdBase):
    """
    listkeypairs

    List all EC2 keypairs
    """
    names = ['listkeypairs', 'lk']

    def execute(self, args):
        self.ec2.list_keypairs()
