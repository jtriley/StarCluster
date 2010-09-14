#!/usr/bin/env python

from base import CmdBase

class CmdListVolumes(CmdBase):
    """
    listvolumes

    List all EBS volumes
    """
    names = ['listvolumes', 'lv']
    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        ec2.list_volumes()
