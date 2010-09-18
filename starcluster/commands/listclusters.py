#!/usr/bin/env python

from starcluster import cluster

from base import CmdBase


class CmdListClusters(CmdBase):
    """
    listclusters

    List all active clusters
    """
    names = ['listclusters', 'lc']

    def execute(self, args):
        cfg = self.cfg
        cluster.list_clusters(cfg)
