from base import CmdBase


class CmdShowBucket(CmdBase):
    """
    showbucket <bucket>

    Show all files in an S3 bucket

    Example:

        $ starcluster showbucket mybucket
    """
    names = ['showbucket', 'sb']

    def execute(self, args):
        if not args:
            self.parser.error('please specify an S3 bucket')
        for arg in args:
            self.s3.list_bucket(arg)
