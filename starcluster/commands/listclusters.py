#!/usr/bin/env python

from completers import ClusterCompleter


class CmdListClusters(ClusterCompleter):
    """
    listclusters [<cluster_tag> ...]

    List all active clusters
    """
    names = ['listclusters', 'lc']

    def execute(self, args):
        self.cm.list_clusters(cluster_groups=args)
