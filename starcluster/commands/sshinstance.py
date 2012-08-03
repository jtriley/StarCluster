import sys
from completers import InstanceCompleter


class CmdSshInstance(InstanceCompleter):
    """
    sshinstance [options] <instance-id> [<remote-command>]

    SSH to an EC2 instance

    Examples:

        $ starcluster sshinstance i-14e9157c
        $ starcluster sshinstance ec2-123-123-123-12.compute-1.amazonaws.com

    You can also execute commands without directly logging in:

        $ starcluster sshinstance i-14e9157c 'cat /etc/hosts'
    """
    names = ['sshinstance', 'si']
    show_dns_names = True

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")
        parser.add_option("-X", "--forward-x11", dest="forward_x11",
                          action="store_true", default=False,
                          help="enable X11 forwarding")
        parser.add_option("-A", "--forward-agent", dest="forward_agent",
                          action="store_true", default=False,
                          help="enable authentication agent forwarding")

    def execute(self, args):
        if not args:
            self.parser.error(
                "please specify an instance id or dns name to connect to")
        instance = args[0]
        cmd = ' '.join(args[1:])
        retval = self.nm.ssh_to_node(instance, user=self.opts.user,
                                     command=cmd,
                                     forward_x11=self.opts.forward_x11,
                                     forward_agent=self.opts.forward_agent)
        if cmd and retval is not None:
            sys.exit(retval)
