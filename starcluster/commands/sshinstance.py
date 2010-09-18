#!/usr/bin/env python

from starcluster import node
from starcluster import config
from starcluster import optcomplete
from starcluster.logger import log

from base import CmdBase


class CmdSshInstance(CmdBase):
    """
    sshintance [options] <instance-id>

    SSH to an EC2 instance

    Examples:

        $ starcluster sshinstance i-14e9157c
        $ starcluster sshinstance ec2-123-123-123-12.compute-1.amazonaws.com

    """
    names = ['sshinstance', 'si']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig().load()
                ec2 = cfg.get_easy_ec2()
                instances = ec2.get_all_instances()
                completion_list = [i.id for i in instances]
                completion_list.extend([i.dns_name for i in instances])
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="USER", action="store",
                          type="string", default='root',
                          help="login as USER (defaults to root)")

    def execute(self, args):
        if not args:
            self.parser.error(
                "please specify an instance id or dns name to connect to")
        for arg in args:
            # user specified dns name or instance id
            instance = args[0]
            node.ssh_to_node(instance, self.cfg, user=self.opts.USER)
