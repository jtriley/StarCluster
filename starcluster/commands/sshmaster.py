import sys
from completers import ClusterCompleter


class CmdSshMaster(ClusterCompleter):
    """
    sshmaster [options] <cluster> [<remote-command>]

    SSH to a cluster's master node

    Example:

        $ sshmaster mycluster

    You can also execute commands without directly logging in:

        $ starcluster sshmaster mycluster 'cat /etc/hosts'
    """
    names = ['sshmaster', 'sm']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        clname = args[0]
        cmd = ' '.join(args[1:])
        retval = self.cm.ssh_to_master(clname, user=self.opts.user,
                                       command=cmd)
        if cmd and retval is not None:
            sys.exit(retval)
