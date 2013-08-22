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

    Do the same but also plot the spot history over time in a web browser:

        $ starcluster spothistory -p m1.small
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
                          help="plot spot history in a web browser")

    def execute(self, args):
        instance_types = ', '.join(sorted(static.INSTANCE_TYPES.keys()))
        if len(args) != 1:
            self.parser.error(
                'please provide an instance type (options: %s)' %
                instance_types)
        instance_type = args[0]
        if not instance_type in static.INSTANCE_TYPES:
            self.parser.error('invalid instance type. possible options: %s' %
                              instance_types)
        start = self.opts.start_time
        end = self.opts.end_time
        if self.opts.days_ago:
            now = datetime.now()
            end = utils.datetime_tuple_to_iso(now)
            start = utils.datetime_tuple_to_iso(
                now - timedelta(days=self.opts.days_ago))
        browser_cmd = self.cfg.globals.get("web_browser")
        self.ec2.get_spot_history(instance_type, start, end,
                                  zone=self.opts.zone, plot=self.opts.plot,
                                  plot_web_browser=browser_cmd)
