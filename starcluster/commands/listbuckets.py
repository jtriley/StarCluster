from base import CmdBase


class CmdListBuckets(CmdBase):
    """
    listbuckets

    List all S3 buckets
    """
    names = ['listbuckets', 'lb']

    def execute(self, args):
        self.s3.list_buckets()
