#!/usr/bin/env python

from base import CmdBase

class CmdListPublic(CmdBase):
    """
    listpublic

    List all public StarCluster images on EC2
    """
    names = ['listpublic', 'lp']
    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        ec2.list_starcluster_public_images()
