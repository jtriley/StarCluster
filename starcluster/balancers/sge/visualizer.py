#!/usr/bin/env python
"""
StarCluster SunGrinEngine stats visualizer module
"""
from datetime import datetime
import os
from starcluster import static
import numpy as np
import matplotlib.pyplot as plt
from starcluster.logger import log


class SGEVisualizer(object):
    stat = None
    filepath = os.path.join(static.TMP_DIR, 'starcluster-sge-stats.csv')
    pngpath = '/Users/rbanerjee/Dropbox/Public/sc/'

    def __init__(self, cluster_tag=None):
        self.cluster_tag = cluster_tag
        log.debug("Initialized visualizer for cluster %s." % self.cluster_tag)
        if len(cluster_tag) > 0:
            self.filepath = os.path.join(static.TMP_DIR,
                'starcluster-%s-sge-stats.csv' % self.cluster_tag)

    def add(self, x, y):
        return float(x) + float(y)

    def record(self, s):
        """
        This function takes an SGEStats object and takes a snapshot to a CSV
        file. It takes an SGEStats object as a parameter. Appends one line to
        the CSV.
        """
        bits = []
        #first field is the time
        now = datetime.utcnow()
        bits.append(now)
        #second field is the number of hosts
        bits.append(s.count_hosts())
        #third field is # of running jobs
        bits.append(len(s.get_running_jobs()))
        #fourth field is # of queued jobs
        bits.append(len(s.get_queued_jobs()))
        #fifth field is total # slots
        bits.append(s.count_total_slots())
        #sixth field is average job duration
        bits.append(s.avg_job_duration())
        #seventh field is average job wait time
        bits.append(s.avg_wait_time())
        #last field is array of loads for hosts
        arr = s.get_loads()
        load_sum = 0
        load_sum = float(reduce(self.add, arr))
        avg_load = load_sum / len(arr)
        bits.append(avg_load)

        #write to file
        f = open(self.filepath, 'a')
        flat = ','.join(str(n) for n in bits)
        #print array to file
        f.write(flat)
        f.write('\n')
        f.close()

    def read(self):
        list = []
        file = open(self.filepath, 'r')
        for line in file:
            line = line.rstrip()
            parts = line.split(',')
            a = [datetime.strptime(parts[0], '%Y-%m-%d %H:%M:%S.%f'),
                 int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]),
                 int(parts[5]), int(parts[6]), float(parts[7])]
            list.append(a)
        file.close()
        names = ['dt', 'hosts', 'running_jobs', 'queued_jobs',
                 'slots', 'avg_duration', 'avg_wait', 'avg_load']
        self.records = np.rec.fromrecords(list, names=','.join(names))

    def graph(self, yaxis, title):
        if self.records == None:
            log.error("ERROR: File hasn't been read() yet.")
            return -1

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(self.records.dt, yaxis)
        ax.grid(True)

        fig.autofmt_xdate()

        filename = self.pngpath + title + '.png'
        plt.savefig(filename, dpi=100)
        log.debug("saved graph %s." % title)
        plt.close(fig)  # close it when its done

    def graph_all(self):
        vals = [['queued', self.records.queued_jobs], \
                ['running', self.records.running_jobs],\
                ['num_hosts', self.records.hosts],\
                #['slots',self.records.slots],\
                ['avg_duration', self.records.avg_duration],\
                ['avg_wait', self.records.avg_wait], \
                ['avg_load', self.records.avg_load]
               ]
        for sub in vals:
            self.graph(sub[1], sub[0])

        log.info("Done making graphs.")
