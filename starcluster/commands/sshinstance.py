# Copyright 2009-2013 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

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
