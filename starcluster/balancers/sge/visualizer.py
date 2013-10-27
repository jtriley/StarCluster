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

"""
StarCluster SunGrinEngine stats visualizer module
"""
import os
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from starcluster.logger import log


class SGEVisualizer(object):
    """
    Stats Visualizer for SGE Load Balancer
    stats_file - file containing SGE load balancer stats
    pngpath - directory to dump the stat plots to
    """
    def __init__(self, stats_file, pngpath):
        self.pngpath = pngpath
        self.stats_file = stats_file
        self.records = None

    def read(self):
        list = []
        file = open(self.stats_file, 'r')
        for line in file:
            parts = line.rstrip().split(',')
            a = [datetime.strptime(parts[0], '%Y-%m-%d %H:%M:%S.%f'),
                 int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]),
                 int(parts[5]), int(parts[6]), float(parts[7])]
            list.append(a)
        file.close()
        names = ['dt', 'hosts', 'running_jobs', 'queued_jobs',
                 'slots', 'avg_duration', 'avg_wait', 'avg_load']
        self.records = np.rec.fromrecords(list, names=','.join(names))

    def graph(self, yaxis, title):
        if self.records is None:
            log.error("ERROR: File hasn't been read() yet.")
            return -1
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(self.records.dt, yaxis)
        ax.grid(True)
        fig.autofmt_xdate()
        filename = os.path.join(self.pngpath, title + '.png')
        plt.savefig(filename, dpi=100)
        log.debug("saved graph %s." % title)
        plt.close(fig)  # close it when its done

    def graph_all(self):
        self.read()
        vals = {'queued': self.records.queued_jobs,
                'running': self.records.running_jobs,
                'num_hosts': self.records.hosts,
                #'slots': self.records.slots,
                'avg_duration': self.records.avg_duration,
                'avg_wait': self.records.avg_wait,
                'avg_load': self.records.avg_load}
        for sub in vals:
            self.graph(vals[sub], sub)
        log.info("Done making graphs.")
