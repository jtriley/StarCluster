#!/usr/bin/env python

from base import CmdBase


class CmdListClusters(CmdBase):
    """
    listclusters [<cluster_tag> ...]

    List all active clusters
    """
    names = ['listclusters', 'lc']

    def execute(self, args):
        self.cm.list_clusters(cluster_groups=args)
