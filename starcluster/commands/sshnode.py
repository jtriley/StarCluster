import sys
from completers import NodeCompleter


class CmdSshNode(NodeCompleter):
    """
    sshnode <cluster> <node> [<remote-command>]

    SSH to a cluster node

    Examples:

        $ starcluster sshnode mycluster master
        $ starcluster sshnode mycluster node001
        ...

    or same thing in shorthand:

        $ starcluster sshnode mycluster 0
        $ starcluster sshnode mycluster 1
        ...

    You can also execute commands without directly logging in:

        $ starcluster sshnode mycluster node001 'cat /etc/hosts'
    """
    names = ['sshnode', 'sn']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")

    def execute(self, args):
        if len(args) < 2:
            self.parser.error(
                "please specify a cluster and node to connect to")
        scluster = args[0]
        node = args[1]
        cmd = ' '.join(args[2:])
        retval = self.cm.ssh_to_cluster_node(scluster, node,
                                             user=self.opts.user, command=cmd)
        if cmd and retval is not None:
            sys.exit(retval)
