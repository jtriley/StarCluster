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
    """
    names = ['spothistory', 'shi']

    def addopts(self, parser):
        now_tup = datetime.now()
        now = utils.datetime_tuple_to_iso(now_tup)
        delta = now_tup - timedelta(days=30)
        thirty_days_ago = utils.datetime_tuple_to_iso(delta)
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

    def execute(self, args):
        instance_types = ', '.join(static.INSTANCE_TYPES.keys())
        if len(args) != 1:
            self.parser.error(
                'please provide an instance type (options: %s)' %
                instance_types)
        instance_type = args[0]
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
        self.ec2.get_spot_history(instance_type, start, end, self.opts.plot,
                                  plot_web_browser=browser_cmd)
