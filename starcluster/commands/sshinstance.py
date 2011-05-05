#!/usr/bin/env python

from completers import InstanceCompleter


class CmdSshInstance(InstanceCompleter):
    """
    sshinstance [options] <instance-id>

    SSH to an EC2 instance

    Examples:

        $ starcluster sshinstance i-14e9157c
        $ starcluster sshinstance ec2-123-123-123-12.compute-1.amazonaws.com

    """
    names = ['sshinstance', 'si']
    show_dns_names = True

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")

    def execute(self, args):
        if not args:
            self.parser.error(
                "please specify an instance id or dns name to connect to")
        for instance in args:
            self.nm.ssh_to_node(instance, user=self.opts.user)
