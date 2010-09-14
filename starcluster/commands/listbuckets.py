#!/usr/bin/env python

from base import CmdBase

class CmdListBuckets(CmdBase):
    """
    listbuckets

    List all S3 buckets
    """
    names = ['listbuckets', 'lb']
    def execute(self, args):
        s3 = self.cfg.get_easy_s3()
        buckets = s3.list_buckets()
