from datetime import datetime, timedelta

from starcluster import utils
from starcluster import static

from base import CmdBase


class CmdSpotHistory(CmdBase):
    """
    spothistory [options] <instance_type>

    Show spot instance pricing history stats (last 30 days by default)

    Examples:

    Show the current, max, and average spot price for m1.small instance type:

        $ starcluster spothistory m1.small

    Do the same but also plot the spot history over time using matplotlib:

        $ starcluster spothistory -p m1.small

    Show it based on a current cluster config and zone

        $ starcluster spothistory -c <cluster-name>
    """
    names = ['spothistory', 'shi']

    def addopts(self, parser):
        now_tup = datetime.now()
        now = utils.datetime_tuple_to_iso(now_tup)
        delta = now_tup - timedelta(days=30)
        thirty_days_ago = utils.datetime_tuple_to_iso(delta)
        parser.add_option("-z", "--zone", dest="zone", default=None,
                          help="limit results to specific availability zone")
        parser.add_option("-d", "--days", dest="days_ago",
                          action="store", type="float",
                          help="provide history in the last DAYS_AGO days "
                          "(overrides -s and -e options)")
        parser.add_option("-s", "--start-time", dest="start_time",
                          action="store", type="string",
                          default=thirty_days_ago,
                          help="show price history after START_TIME "
                          "(e.g. 2010-01-15T22:22:22)")
        parser.add_option("-e", "--end-time", dest="end_time",
                          action="store", type="string", default=now,
                          help="show price history up until END_TIME "
                          "(e.g. 2010-02-15T22:22:22)")
        parser.add_option("-p", "--plot", dest="plot",
                          action="store_true", default=False,
                          help="plot spot history using matplotlib")
        parser.add_option("-c", "--cluster-name", dest="cluster_name", 
                          default=None,
                          help="limit results to the clusters master node "
                          "availability zone")

    def execute(self, args):
        instance_types = ', '.join(static.INSTANCE_TYPES.keys())

        zone = None
        instance_type = None
        if self.opts.cluster_name:
            cl = self.cm.get_cluster(self.opts.cluster_name, 
                                     require_keys=False)
            instance_type = cl.node_instance_type
            zone = cl.nodes[0].placement
            self.log.info("Cluster zone: " + zone)
            self.log.info("Clustter node instance type: " + instance_type)
        if self.opts.zone:
            if zone:
                self.log.info("You specified a zone and a cluster to get the zone "
                              "from. Using the cluster zone.")
            else:
                zone = self.opts.zone
                self.log.info("Specified zone: " + zone)
        if instance_type: 
            if len(args) == 1:
                self.log.info("You provided an instance type and a cluster to "
                              "get the instance type from. Using the cluster "
                              "instance type.")
            
        elif len(args) != 1:
            self.parser.error(
                'please provide an instance type (options: %s)' %
                instance_types)
        else:
            instance_type = args[0]
            self.log.info("Specified instance type: " + instance_type)
            if not instance_type in static.INSTANCE_TYPES:
                self.parser.error('invalid instance type. possible options: %s' %
                                  ', '.join(static.INSTANCE_TYPES))
        start = self.opts.start_time
        end = self.opts.end_time
        if self.opts.days_ago:
            now = datetime.now()
            end = utils.datetime_tuple_to_iso(now)
            start = utils.datetime_tuple_to_iso(
                now - timedelta(days=self.opts.days_ago))
        browser_cmd = self.cfg.globals.get("web_browser")


        self.ec2.get_spot_history(instance_type, start, end, zone, 
                                  self.opts.plot, plot_web_browser=browser_cmd)
