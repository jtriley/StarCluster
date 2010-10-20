#!/usr/bin/env python

from starcluster.balancers import sge

from completers import ClusterCompleter


class CmdLoadBalance(ClusterCompleter):
    """
    loadbalance <cluster_tag>

    Start the SGE Load Balancer.
    """

    names = ['loadbalance', 'bal']

    def addopts(self, parser):
        parser.add_option("-p", "--plot", dest="plot",
                          action="store_true", default=False,
                          help="Plot usage data at each iteration")
        parser.add_option("-i", "--interval", dest="interval",
                          action="store", type="int", default=None,
                          help="Polling interval for load balancer")
        parser.add_option("-m", "--max_nodes",dest="max_nodes",
                          action="store", type="int", default=None,
                          help="Maximum # of nodes in cluster")
        parser.add_option("-w", "--job_wait_time",dest="wait_time",
                          action="store", type="int", default=None,
                          help=("Maximum wait time for a job before " + \
                                "adding nodes, seconds"))
        parser.add_option("-a", "--add_nodes_per_iter",dest="add_pi",
                          action="store", type="int", default=None,
                          help="Number of nodes to add per iteration")
        parser.add_option("-k", "--kill_after", dest="kill_after",
                          action="store", type="int", default=None,
                          help="Minutes after which a node can be killed")
        parser.add_option("-s", "--stabilization_time", dest="stab",
                          action="store", type="int", default=None,
                          help="Seconds to wait before cluster stabilizes")
        parser.add_option("-l", "--lookback_window", dest="lookback_win",
                          action="store", type="int", default=None,
                          help="Minutes to look back for past job history")
        parser.add_option("-n", "--min_nodes", dest="min_nodes",
                          action="store", type="int", default=None,
                          help="Minimum number of nodes in cluster")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a <cluster_tag>")
        cluster_tag = args[0]
        lb = sge.SGELoadBalancer(cluster_tag, self.cfg,
                                 **self.specified_options_dict)
        lb.run()
