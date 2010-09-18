#!/usr/bin/env python

from base import CmdBase


class CmdListRegions(CmdBase):
    """
    listregions

    List all EC2 regions
    """
    names = ['listregions', 'lr']

    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        ec2.list_regions()
