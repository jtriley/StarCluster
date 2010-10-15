#!/usr/bin/env python

from starcluster import config
from starcluster import optcomplete
from starcluster.logger import log

from base import CmdBase


class CmdShowConsole(CmdBase):
    """
    showconsole <instance-id>

    Show console output for an EC2 instance

    Example:

        $ starcluster showconsole i-999999

    This will display the startup logs for instance i-999999
    """
    names = ['showconsole', 'sc']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig().load()
                ec2 = cfg.get_easy_ec2()
                instances = ec2.get_all_instances()
                completion_list = [i.id for i in instances]
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def execute(self, args):
        if not len(args) == 1:
            self.parser.error('please provide an instance id')
        instance_id = args[0]
        self.ec2.show_console_output(instance_id)
