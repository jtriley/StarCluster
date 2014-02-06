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

from datetime import timedelta

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

    Do the same but also plot the spot history over time in a web browser:

        $ starcluster spothistory -p m1.small
    """
    names = ['spothistory', 'shi']

    def addopts(self, parser):
        parser.add_option("-z", "--zone", dest="zone", default=None,
                          help="limit results to specific availability zone")
        parser.add_option("-d", "--days", dest="days_ago",
                          action="store", type="float", default=None,
                          help="provide history in the last DAYS_AGO days "
                          "(overrides -s option)")
        parser.add_option("-s", "--start-time", dest="start_time",
                          action="callback", type="string", default=None,
                          callback=self._iso_timestamp,
                          help="show price history after START_TIME (UTC)"
                          "(e.g. 2010-01-15T22:22:22Z)")
        parser.add_option("-e", "--end-time", dest="end_time",
                          action="callback", type="string", default=None,
                          callback=self._iso_timestamp,
                          help="show price history up until END_TIME (UTC)"
                          "(e.g. 2010-02-15T22:22:22Z)")
        parser.add_option("-p", "--plot", dest="plot",
                          action="store_true", default=False,
                          help="plot spot history in a web browser")
        parser.add_option("-v", "--vpc", dest="vpc",
                          action="store_true", default=False,
                          help="show spot prices for VPC")
        parser.add_option("-c", "--classic", dest="classic",
                          action="store_true", default=False,
                          help="show spot prices for EC2-Classic")

    def execute(self, args):
        instance_types = ', '.join(sorted(static.INSTANCE_TYPES.keys()))
        if len(args) != 1:
            self.parser.error(
                'please provide an instance type (options: %s)' %
                instance_types)
        if self.opts.classic and self.opts.vpc:
            self.parser.error("options -c and -v cannot be specified at "
                              "the same time")
        instance_type = args[0]
        if not instance_type in static.INSTANCE_TYPES:
            self.parser.error('invalid instance type. possible options: %s' %
                              instance_types)
        start = self.opts.start_time
        end = self.opts.end_time
        if self.opts.days_ago:
            if self.opts.start_time:
                self.parser.error("options -d and -s cannot be specified at "
                                  "the same time")
            if self.opts.end_time:
                end_tup = utils.iso_to_datetime_tuple(self.opts.end_time)
            else:
                end_tup = utils.get_utc_now()
            start = utils.datetime_tuple_to_iso(
                end_tup - timedelta(days=self.opts.days_ago))
        browser_cmd = self.cfg.globals.get("web_browser")
        self.ec2.get_spot_history(instance_type, start, end,
                                  zone=self.opts.zone, plot=self.opts.plot,
                                  plot_web_browser=browser_cmd,
                                  vpc=self.opts.vpc,
                                  classic=self.opts.classic)
