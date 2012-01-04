from base import CmdBase


class CmdListInstances(CmdBase):
    """
    listinstances [options]

    List all running EC2 instances
    """
    names = ['listinstances', 'lsi']

    def addopts(self, parser):
        parser.add_option("-t", "--show-terminated", dest="show_terminated",
                          action="store_true", default=False,
                          help="show terminated instances")

    def execute(self, args):
        self.ec2.list_all_instances(self.opts.show_terminated)
