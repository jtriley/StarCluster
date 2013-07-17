# Copyright 2009-2013 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

from starcluster import exception
from starcluster.balancers import sge

from completers import ClusterCompleter


class CmdLoadBalance(ClusterCompleter):
    """
    loadbalance <cluster_tag>

    Start the SGE Load Balancer.

    Example:

        $ starcluster loadbalance mycluster

    This command will endlessly attempt to monitor and load balance 'mycluster'
    based on the current SGE load. You can also have the load balancer plot the
    various stats it's monitoring over time using the --plot-stats option:

        $ starcluster loadbalance -p mycluster

    If you just want the stats data and not the plots use the --dump-stats
    option instead:

        $ starcluster loadbalance -d mycluster

    See "starcluster loadbalance --help" for more details on the '-p' and '-d'
    options as well as other options for tuning the SGE load balancer
    algorithm.
    """

    names = ['loadbalance', 'bal']

    def addopts(self, parser):
        parser.add_option("-d", "--dump-stats", dest="dump_stats",
                          action="store_true", default=False,
                          help="Output stats to a csv file at each iteration")
        parser.add_option("-D", "--dump-stats-file", dest="stats_file",
                          action="store", default=None,
                          help="File to dump stats to (default: %s)" %
                          sge.DEFAULT_STATS_FILE % "<cluster_tag>")
        parser.add_option("-p", "--plot-stats", dest="plot_stats",
                          action="store_true", default=False,
                          help="Plot usage stats at each iteration")
        parser.add_option("-P", "--plot-output-dir", dest="plot_output_dir",
                          action="store", default=None,
                          help="Output directory for stats plots "
                          "(default: %s)" % sge.DEFAULT_STATS_DIR %
                          "<cluster_tag>")
        parser.add_option("-i", "--interval", dest="interval",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Load balancer polling interval in seconds "
                          "(max: 300s)")
        parser.add_option("-m", "--max_nodes", dest="max_nodes",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Maximum # of nodes in cluster")
        parser.add_option("-w", "--job_wait_time", dest="wait_time",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help=("Maximum wait time for a job before "
                                "adding nodes, seconds"))
        parser.add_option("-a", "--add_nodes_per_iter", dest="add_pi",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Number of nodes to add per iteration")
        parser.add_option("-k", "--kill_after", dest="kill_after",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Minutes after which a node can be killed")
        parser.add_option("-s", "--stabilization_time", dest="stab",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Seconds to wait before cluster "
                          "stabilizes (min: 300s)")
        parser.add_option("-l", "--lookback_window", dest="lookback_win",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Minutes to look back for past job history")
        parser.add_option("-n", "--min_nodes", dest="min_nodes",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="Minimum number of nodes in cluster")
        parser.add_option("-K", "--kill-cluster", dest="kill_cluster",
                          action="store_true", default=False,
                          help="Terminate the cluster when the queue is empty")

    def execute(self, args):
        if not self.cfg.globals.enable_experimental:
            raise exception.ExperimentalFeature("The 'loadbalance' command")
        if len(args) != 1:
            self.parser.error("please specify a <cluster_tag>")
        cluster_tag = args[0]
        cluster = self.cm.get_cluster(cluster_tag)
        lb = sge.SGELoadBalancer(**self.specified_options_dict)
        lb.run(cluster)
