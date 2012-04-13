from starcluster import exception
from starcluster.balancers import sge

from completers import ClusterCompleter

##changes
#   added A, I, z,b, q , h and S options

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
                          action="store", type="int", default=None,
                          help="Load balancer polling interval in seconds "
                          "(max: 300s)")
        parser.add_option("-m", "--max_nodes", dest="max_nodes",
                          action="store", type="int", default=None,
                          help="Maximum # of nodes in cluster")
        parser.add_option("-w", "--job_wait_time", dest="wait_time",
                          action="store", type="int", default=None,
                          help=("Maximum wait time for a job before "
                                "adding nodes, seconds"))
        parser.add_option("-a", "--add_nodes_per_iter", dest="add_pi",
                          action="store", type="int", default=None,
                          help="Number of nodes to add per iteration")
        parser.add_option("-k", "--kill_after", dest="kill_after",
                          action="store", type="int", default=None,
                          help="Minutes after which a node can be killed")
        parser.add_option("-s", "--stabilization_time", dest="stab",
                          action="store", type="int", default=None,
                          help="Seconds to wait before cluster "
                          "stabilizes (min: 300s)")
        parser.add_option("-l", "--lookback_window", dest="lookback_win",
                          action="store", type="int", default=None,
                          help="Minutes to look back for past job history")
        parser.add_option("-n", "--min_nodes", dest="min_nodes",
                          action="store", type="int", default=None,
                          help="Minimum number of nodes in cluster")
<<<<<<< HEAD
        parser.add_option("-K", "--kill-master", dest="allow_master_kill",
                          action="store_true", default=None,
                          help="Allow the master to be killed when "
                          "the queue is empty (EXPERIMENTAL).")
        parser.add_option("-A", "--image-id", type="string", dest="image_id",
                          action="store_true", default=None,
                          help="AMI image id to use when adding nodes")
        parser.add_option("-I", "--instance-type", dest="instance_type",
                          action="store_true", type="string", default=None,
                          help="Instance type to use when adding nodes")
        parser.add_option("-z", "--availability-zone", dest="zone",
                          action="store_true", type="string", default=None,
                          help="Availability zone to use when adding nodes")
        parser.add_option("-b", "--bid", dest="spot_bid",
                          action="store_true", type="float", default=None,
                          help="Spot bid to use when adding nodes")
        parser.add_option("-q", "--queue-name", dest="queue_name",
                          action="store_true", type="string", default='all.q',
                          help="queue to balance (defaults to all.q)")
        parser.add_option("-h", "--host-group", dest="host_group",
                          action="store_true", type="string", default=None,
                          help="host group to add nodes to")  
        parser.add_option("-S", "--slots", dest="slots",
                          action="store_true", type="int", default=None,
                          help="number of slots to declare when adding nodes "
                          "(defaults to number of cpus on machine)")  
            
=======
        parser.add_option("-K", "--kill-cluster", dest="kill_cluster",
                          action="store_true", default=False,
                          help="Terminate the cluster when the queue is empty")
>>>>>>> upstream/master

    def execute(self, args):
        if not self.cfg.globals.enable_experimental:
            raise exception.ExperimentalFeature("The 'loadbalance' command")
        if len(args) != 1:
            self.parser.error("please specify a <cluster_tag>")
        cluster_tag = args[0]
        cluster = self.cm.get_cluster(cluster_tag)
        lb = sge.SGELoadBalancer(**self.specified_options_dict)
        lb.run(cluster)
