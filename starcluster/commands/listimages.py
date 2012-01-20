from base import CmdBase


class CmdListImages(CmdBase):
    """
    listimages [options]

    List all registered EC2 images (AMIs)
    """
    names = ['listimages', 'li']

    def addopts(self, parser):
        parser.add_option(
            "-x", "--executable-by-me", dest="executable",
            action="store_true", default=False,
            help=("Show images owned by other users that " +
                  "you have permission to execute"))

    def execute(self, args):
        if self.opts.executable:
            self.ec2.list_executable_images()
        else:
            self.ec2.list_registered_images()
