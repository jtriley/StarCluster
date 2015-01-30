# Copyright 2009-2014 Justin Riley
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

import os
import re
import time
import datetime
import xml.dom.minidom

from starcluster import utils
from starcluster import static
from starcluster import exception
from starcluster.balancers import LoadBalancer
from starcluster.logger import log


SGE_STATS_DIR = os.path.join(static.STARCLUSTER_CFG_DIR, 'sge')
DEFAULT_STATS_DIR = os.path.join(SGE_STATS_DIR, '%s')
DEFAULT_STATS_FILE = os.path.join(DEFAULT_STATS_DIR, 'sge-stats.csv')


class SGEStats(object):
    """
    SunGridEngine stats parser
    """
    def __init__(self, remote_tzinfo=None):
        self.jobstat_cachesize = 200
        self.hosts = []
        self.jobs = []
        self.queues = {}
        self.jobstats = self.jobstat_cachesize * [None]
        self.max_job_id = 0
        self.remote_tzinfo = remote_tzinfo or utils.get_utc_now().tzinfo

    @property
    def first_job_id(self):
        if self.jobs:
            return int(self.jobs[0]['JB_job_number'])

    @property
    def last_job_id(self):
        if self.jobs:
            return int(self.jobs[-1]['JB_job_number'])

    def parse_qhost(self, qhost_out):
        """
        this function parses qhost -xml output and makes a neat array
        takes in a string, so we can pipe in output from ssh.exec('qhost -xml')
        """
        self.hosts = []  # clear the old hosts
        doc = xml.dom.minidom.parseString(qhost_out)
        for h in doc.getElementsByTagName("host"):
            name = h.getAttribute("name")
            hash = {"name": name}
            for stat in h.getElementsByTagName("hostvalue"):
                for hvalue in stat.childNodes:
                    attr = stat.attributes['name'].value
                    val = ""
                    if hvalue.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                        val = hvalue.data
                    hash[attr] = val
            if hash['name'] != u'global':
                self.hosts.append(hash)
        return self.hosts

    def parse_qstat(self, qstat_out):
        """
        This method parses qstat -xml output and makes a neat array
        """
        self.jobs = []  # clear the old jobs
        self.queues = {}  # clear the old queues
        doc = xml.dom.minidom.parseString(qstat_out)
        for q in doc.getElementsByTagName("Queue-List"):
            name = q.getElementsByTagName("name")[0].childNodes[0].data
            slots = q.getElementsByTagName("slots_total")[0].childNodes[0].data
            self.queues[name] = dict(slots=int(slots))
            for job in q.getElementsByTagName("job_list"):
                self.jobs.extend(self._parse_job(job, queue_name=name))
        for job in doc.getElementsByTagName("job_list"):
            if job.parentNode.nodeName == 'job_info':
                self.jobs.extend(self._parse_job(job))
        return self.jobs

    def _parse_job(self, job, queue_name=None):
        jstate = job.getAttribute("state")
        jdict = dict(job_state=jstate, queue_name=queue_name)
        for node in job.childNodes:
            if node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
                for child in node.childNodes:
                    jdict[node.nodeName] = child.data
        num_tasks = self._count_tasks(jdict)
        log.debug("Job contains %d tasks" % num_tasks)
        return [jdict] * num_tasks

    def _count_tasks(self, jdict):
        """
        This function returns the number of tasks in a task array job. For
        example, 'qsub -t 1-20:1' returns 20.
        """
        tasks = jdict.get('tasks', '').split(',')
        num_tasks = 0
        for task in tasks:
            if '-' in task:
                regex = "(\d+)-?(\d+)?:?(\d+)?"
                r = re.compile(regex)
                start, end, step = r.match(task).groups()
                start = int(start)
                end = int(end)
                step = int(step) if step else 1
                num_tasks += (end - start) / step + 1
            else:
                num_tasks += 1
        log.debug("task array job has %s tasks (tasks: %s)" %
                  (num_tasks, tasks))
        return num_tasks

    def qacct_to_datetime_tuple(self, qacct):
        """
        Takes the SGE qacct formatted time and makes a datetime tuple
        format is:
        Tue Jul 13 16:24:03 2010
        """
        dt = datetime.datetime.strptime(qacct, "%a %b %d %H:%M:%S %Y")
        return dt.replace(tzinfo=self.remote_tzinfo)

    def parse_qacct(self, string, dtnow):
        """
        This method parses qacct -j output and makes a neat array and
        calculates some statistics.
        Takes the string to parse, and a datetime object of the remote
        host's current time.
        """
        job_id = None
        qd = None
        start = None
        end = None
        counter = 0
        lines = string.split('\n')
        for l in lines:
            l = l.strip()
            if l.find('jobnumber') != -1:
                job_id = int(l[13:len(l)])
            if l.find('qsub_time') != -1:
                qd = self.qacct_to_datetime_tuple(l[13:len(l)])
            if l.find('start_time') != -1:
                if l.find('-/-') > 0:
                    start = dtnow
                else:
                    start = self.qacct_to_datetime_tuple(l[13:len(l)])
            if l.find('end_time') != -1:
                if l.find('-/-') > 0:
                    end = dtnow
                else:
                    end = self.qacct_to_datetime_tuple(l[13:len(l)])
            if l.find('==========') != -1:
                if qd is not None:
                    self.max_job_id = job_id
                    hash = {'queued': qd, 'start': start, 'end': end}
                    self.jobstats[job_id % self.jobstat_cachesize] = hash
                qd = None
                start = None
                end = None
                counter = counter + 1
        log.debug("added %d new jobs" % counter)
        log.debug("There are %d items in the jobstats cache" %
                  len(self.jobstats))
        return self.jobstats

    def is_jobstats_empty(self):
        """
        This function will return True if half of the queue is empty, False if
        there are enough entries in it.
        """
        return self.max_job_id < (self.jobstat_cachesize * 0.3)

    def get_running_jobs(self):
        """
        returns an array of the running jobs, values stored in dictionary
        """
        running = []
        for j in self.jobs:
            if j['job_state'] == u'running':
                running.append(j)
        return running

    def get_queued_jobs(self):
        """
        returns an array of the queued jobs, values stored in dictionary
        """
        queued = []
        for j in self.jobs:
            if j['job_state'] == u'pending' and j['state'] == u'qw':
                queued.append(j)
        return queued

    def count_hosts(self):
        """
        returns a count of the hosts in the cluster
        """
        # todo: throw an exception if hosts not initialized
        return len(self.hosts)

    def count_total_slots(self):
        """
        Returns a count of the total slots available in this cluster
        """
        slots = 0
        for q in self.queues:
            if q.startswith('all.q@'):
                slots += self.queues.get(q).get('slots')
        return slots

    def slots_per_host(self):
        """
        Returns the number of slots per host. If for some reason the cluster is
        inconsistent, this will return -1 for example, if you have m1.large and
        m1.small in the same cluster
        """
        total = self.count_total_slots()
        if total == 0:
            return total
        single = 0
        for q in self.queues:
            if q.startswith('all.q@'):
                single = self.queues.get(q).get('slots')
                break
        if (total != (single * len(self.hosts))):
            raise exception.BaseException(
                "ERROR: Number of slots not consistent across cluster")
        return single

    def oldest_queued_job_age(self):
        """
        This returns the age of the oldest job in the queue in normal waiting
        state
        """
        for j in self.jobs:
            if 'JB_submission_time' in j and j['state'] == 'qw':
                st = j['JB_submission_time']
                dt = utils.iso_to_datetime_tuple(st)
                return dt.replace(tzinfo=self.remote_tzinfo)
        # todo: throw a "no queued jobs" exception

    def is_node_working(self, node):
        """
        This function returns true if the node is currently working on a task,
        or false if the node is currently idle.
        """
        nodename = node.alias
        for j in self.jobs:
            qn = j.get('queue_name', '')
            if nodename in qn:
                log.debug("Node %s is working" % node.alias)
                return True
        log.debug("Node %s is IDLE" % node.id)
        return False

    def num_slots_for_job(self, job_id):
        """
        returns the number of slots requested for the given job id
        returns None if job_id is invalid
        """
        ujid = unicode(job_id)
        for j in self.jobs:
            if j['JB_job_number'] == ujid:
                return int(j['slots'])

    def avg_job_duration(self):
        count = 0
        total_seconds = 0
        for job in self.jobstats:
            if job is not None:
                delta = job['end'] - job['start']
                total_seconds += delta.seconds
                count += 1
        if count == 0:
            return count
        else:
            return total_seconds / count

    def avg_wait_time(self):
        count = 0
        total_seconds = 0
        for job in self.jobstats:
            if job is not None:
                delta = job['start'] - job['queued']
                total_seconds += delta.seconds
                count += 1
        if count == 0:
            return count
        else:
            return total_seconds / count

    def get_loads(self):
        """
        returns an array containing the loads on each host in cluster
        """
        loads = []
        for h in self.hosts:
            load_avg = h['load_avg']
            try:
                if load_avg == "-":
                    load_avg = 0
                elif load_avg[-1] == 'K':
                    load_avg = float(load_avg[:-1]) * 1000
            except TypeError:
                # load_avg was already a number
                pass
            loads.append(load_avg)
        return loads

    def _add(self, x, y):
        return float(x) + float(y)

    def get_all_stats(self):
        now = utils.get_utc_now()
        bits = []
        # first field is the time
        bits.append(now)
        # second field is the number of hosts
        bits.append(self.count_hosts())
        # third field is # of running jobs
        bits.append(len(self.get_running_jobs()))
        # fourth field is # of queued jobs
        bits.append(len(self.get_queued_jobs()))
        # fifth field is total # slots
        bits.append(self.count_total_slots())
        # sixth field is average job duration
        bits.append(self.avg_job_duration())
        # seventh field is average job wait time
        bits.append(self.avg_wait_time())
        # last field is array of loads for hosts
        arr = self.get_loads()
        # arr may be empty if there are no exec hosts
        if arr:
            load_sum = float(reduce(self._add, arr))
            avg_load = load_sum / len(arr)
        else:
            avg_load = 0.0
        bits.append(avg_load)
        return bits

    def write_stats_to_csv(self, filename):
        """
        Write important SGE stats to CSV file
        Appends one line to the CSV
        """
        bits = self.get_all_stats()
        try:
            f = open(filename, 'a')
            flat = ','.join(str(n) for n in bits) + '\n'
            f.write(flat)
            f.close()
        except IOError, e:
            raise exception.BaseException(str(e))


class SGELoadBalancer(LoadBalancer):
    """
    This class is able to query each SGE host and return load & queue
    statistics

    *** All times are in SECONDS unless otherwise specified ***

    The polling interval in seconds. Must be <= 300 seconds. The polling loop
    with visualizer takes about 15 seconds.
    polling_interval = 60

    VERY IMPORTANT: Set this to the max nodes you're willing to have in your
    cluster. Try setting this to the default cluster size you'd ordinarily use.
    max_nodes = 5

    IMPORTANT: Set this to the longest time a job can wait before another host
    is added to the cluster to help. Must be at least 300 seconds. Recommended:
    300 - 900 secs (5-15 mins). The minimum value is 300 seconds because that's
    approximately how long an instance will take to start up.
    wait_time = 900

    Keep this at 1 - your master, for now.
    min_nodes = 1

    This would allow the master to be killed when the queue empties. UNTESTED.
    kill_cluster = False

    How many nodes to add per iteration. Setting it > 1 opens up possibility
    of spending too much $$
    add_nodes_per_iteration = 1

    Kill an instance after it is idle and has been up for X minutes. Do not
    kill earlier, since you've already paid for that hour. (in mins)
    kill_after = 45

    After adding a node, how long to wait for the instance to start new jobs
    stabilization_time = 180

    Visualizer off by default. Start it with "starcluster loadbalance -p tag"
    plot_stats = False

    How many hours qacct should look back to gather past job data. lower
    values minimize data transfer
    lookback_window = 3
    """

    def __init__(self, interval=60, max_nodes=None, wait_time=900,
                 add_pi=1, kill_after=45, stab=180, lookback_win=3,
                 min_nodes=None, kill_cluster=False, plot_stats=False,
                 plot_output_dir=None, dump_stats=False, stats_file=None):
        self._cluster = None
        self._keep_polling = True
        self._visualizer = None
        self._stat = None
        self.__last_cluster_mod_time = utils.get_utc_now()
        self.polling_interval = interval
        self.kill_after = kill_after
        self.longest_allowed_queue_time = wait_time
        self.add_nodes_per_iteration = add_pi
        self.stabilization_time = stab
        self.lookback_window = lookback_win
        self.kill_cluster = kill_cluster
        self.max_nodes = max_nodes
        self.min_nodes = min_nodes
        self.dump_stats = dump_stats
        self.stats_file = stats_file
        self.plot_stats = plot_stats
        self.plot_output_dir = plot_output_dir
        if plot_stats:
            assert self.visualizer is not None

    @property
    def stat(self):
        if not self._stat:
            rtime = self.get_remote_time()
            self._stat = SGEStats(remote_tzinfo=rtime.tzinfo)
        return self._stat

    @property
    def visualizer(self):
        if not self._visualizer:
            try:
                from starcluster.balancers.sge import visualizer
            except ImportError, e:
                log.error("Error importing visualizer:")
                log.error(str(e))
                log.error("check that matplotlib and numpy are installed and:")
                log.error("   $ python -c 'import matplotlib'")
                log.error("   $ python -c 'import numpy'")
                log.error("completes without error")
                raise exception.BaseException(
                    "Failed to load stats visualizer")
            self._visualizer = visualizer.SGEVisualizer(self.stats_file,
                                                        self.plot_output_dir)
        else:
            self._visualizer.stats_file = self.stats_file
            self._visualizer.pngpath = self.plot_output_dir
        return self._visualizer

    def _validate_dir(self, dirname, msg_prefix=""):
        if not os.path.isdir(dirname):
            msg = "'%s' is not a directory"
            if not os.path.exists(dirname):
                msg = "'%s' does not exist"
            if msg_prefix:
                msg = ' '.join([msg_prefix, msg])
            msg = msg % dirname
            raise exception.BaseException(msg)

    def _mkdir(self, directory, makedirs=False):
        if not os.path.isdir(directory):
            if os.path.isfile(directory):
                raise exception.BaseException("'%s' is a file not a directory")
            try:
                if makedirs:
                    os.makedirs(directory)
                    log.info("Created directories %s" % directory)
                else:
                    os.mkdir(directory)
                    log.info("Created single directory %s" % directory)
            except IOError, e:
                raise exception.BaseException(str(e))

    def get_remote_time(self):
        """
        This function remotely executes 'date' on the master node
        and returns a datetime object with the master's time
        instead of fetching it from local machine, maybe inaccurate.
        """
        cmd = 'date --iso-8601=seconds'
        date_str = '\n'.join(self._cluster.master_node.ssh.execute(cmd))
        d = utils.iso_to_datetime_tuple(date_str)
        if self._stat:
            self._stat.remote_tzinfo = d.tzinfo
        return d

    def get_qatime(self, now):
        """
        This function takes the lookback window and creates a string
        representation of the past few hours, to feed to qacct to
        limit the dataset qacct returns.
        """
        if self.stat.is_jobstats_empty():
            log.info("Loading full job history")
            temp_lookback_window = self.lookback_window * 60 * 60
        else:
            temp_lookback_window = self.polling_interval
        log.debug("getting past %d seconds worth of job history" %
                  temp_lookback_window)
        now = now - datetime.timedelta(seconds=temp_lookback_window + 1)
        return now.strftime("%Y%m%d%H%M")

    def _get_stats(self):
        master = self._cluster.master_node
        now = self.get_remote_time()
        qatime = self.get_qatime(now)
        qacct_cmd = 'qacct -j -b ' + qatime
        qstat_cmd = 'qstat -u \* -xml -f -r'
        qhostxml = '\n'.join(master.ssh.execute('qhost -xml'))
        qstatxml = '\n'.join(master.ssh.execute(qstat_cmd))
        try:
            qacct = '\n'.join(master.ssh.execute(qacct_cmd))
        except exception.RemoteCommandFailed:
            if master.ssh.isfile('/opt/sge6/default/common/accounting'):
                raise
            else:
                log.info("No jobs have completed yet!")
                qacct = ''
        self.stat.parse_qhost(qhostxml)
        self.stat.parse_qstat(qstatxml)
        self.stat.parse_qacct(qacct, now)
        log.debug("sizes: qhost: %d, qstat: %d, qacct: %d" %
                  (len(qhostxml), len(qstatxml), len(qacct)))
        return self.stat

    @utils.print_timing("Fetching SGE stats", debug=True)
    def get_stats(self):
        """
        This method will ssh to the SGE master and get load & queue stats. It
        will feed these stats to SGEStats, which parses the XML. It will return
        two arrays: one of hosts, each host has a hash with its host
        information inside. The job array contains a hash for every job,
        containing statistics about the job name, priority, etc.
        """
        log.debug("starting get_stats")
        retries = 5
        for i in range(retries):
            try:
                return self._get_stats()
            except Exception:
                log.warn("Failed to retrieve stats (%d/%d):" %
                         (i + 1, retries), exc_info=True)
                log.warn("Retrying in %ds" % self.polling_interval)
                time.sleep(self.polling_interval)
        raise exception.BaseException(
            "Failed to retrieve SGE stats after trying %d times, exiting..." %
            retries)

    def run(self, cluster):
        """
        This function will loop indefinitely, using SGELoadBalancer.get_stats()
        to get the clusters status. It looks at the job queue and tries to
        decide whether to add or remove a node.  It should later look at job
        durations (currently doesn't)
        """
        self._cluster = cluster
        if self.max_nodes is None:
            self.max_nodes = cluster.cluster_size
        if self.min_nodes is None:
            self.min_nodes = 1
        if self.kill_cluster:
            self.min_nodes = 0
        if self.min_nodes > self.max_nodes:
            raise exception.BaseException(
                "min_nodes cannot be greater than max_nodes")
        use_default_stats_file = self.dump_stats and not self.stats_file
        use_default_plots_dir = self.plot_stats and not self.plot_output_dir
        if use_default_stats_file or use_default_plots_dir:
            self._mkdir(DEFAULT_STATS_DIR % cluster.cluster_tag, makedirs=True)
        if not self.stats_file:
            self.stats_file = DEFAULT_STATS_FILE % cluster.cluster_tag
        if not self.plot_output_dir:
            self.plot_output_dir = DEFAULT_STATS_DIR % cluster.cluster_tag
        if not cluster.is_cluster_up():
            raise exception.ClusterNotRunning(cluster.cluster_tag)
        if self.dump_stats:
            if os.path.isdir(self.stats_file):
                raise exception.BaseException("stats file destination '%s' is"
                                              " a directory" % self.stats_file)
            sfdir = os.path.dirname(os.path.abspath(self.stats_file))
            self._validate_dir(sfdir, msg_prefix="stats file destination")
        if self.plot_stats:
            if os.path.isfile(self.plot_output_dir):
                raise exception.BaseException("plot output destination '%s' "
                                              "is a file" %
                                              self.plot_output_dir)
            self._validate_dir(self.plot_output_dir,
                               msg_prefix="plot output destination")
        raw = dict(__raw__=True)
        log.info("Starting load balancer (Use ctrl-c to exit)")
        log.info("Maximum cluster size: %d" % self.max_nodes,
                 extra=raw)
        log.info("Minimum cluster size: %d" % self.min_nodes,
                 extra=raw)
        log.info("Cluster growth rate: %d nodes/iteration\n" %
                 self.add_nodes_per_iteration, extra=raw)
        if self.dump_stats:
            log.info("Writing stats to file: %s" % self.stats_file)
        if self.plot_stats:
            log.info("Plotting stats to directory: %s" % self.plot_output_dir)
        while(self._keep_polling):
            if not cluster.is_cluster_up():
                log.info("Waiting for all nodes to come up...")
                time.sleep(self.polling_interval)
                continue
            self.get_stats()
            log.info("Execution hosts: %d" % len(self.stat.hosts), extra=raw)
            log.info("Queued jobs: %d" % len(self.stat.get_queued_jobs()),
                     extra=raw)
            oldest_queued_job_age = self.stat.oldest_queued_job_age()
            if oldest_queued_job_age:
                log.info("Oldest queued job: %s" % oldest_queued_job_age,
                         extra=raw)
            log.info("Avg job duration: %d secs" %
                     self.stat.avg_job_duration(), extra=raw)
            log.info("Avg job wait time: %d secs" % self.stat.avg_wait_time(),
                     extra=raw)
            log.info("Last cluster modification time: %s" %
                     self.__last_cluster_mod_time.strftime("%Y-%m-%d %X%z"),
                     extra=dict(__raw__=True))
            # evaluate if nodes need to be added
            self._eval_add_node()
            # evaluate if nodes need to be removed
            self._eval_remove_node()
            if self.dump_stats or self.plot_stats:
                self.stat.write_stats_to_csv(self.stats_file)
            # call the visualizer
            if self.plot_stats:
                try:
                    self.visualizer.graph_all()
                except IOError, e:
                    raise exception.BaseException(str(e))
            # evaluate if cluster should be terminated
            if self.kill_cluster:
                if self._eval_terminate_cluster():
                    log.info("Terminating cluster and exiting...")
                    return self._cluster.terminate_cluster()
            log.info("Sleeping...(looping again in %d secs)\n" %
                     self.polling_interval)
            time.sleep(self.polling_interval)

    def has_cluster_stabilized(self):
        now = utils.get_utc_now()
        elapsed = (now - self.__last_cluster_mod_time).seconds
        is_stabilized = not (elapsed < self.stabilization_time)
        if not is_stabilized:
            log.info("Cluster was modified less than %d seconds ago" %
                     self.stabilization_time)
            log.info("Waiting for cluster to stabilize...")
        return is_stabilized

    def _eval_add_node(self):
        """
        This function inspects the current state of the SGE queue and decides
        whether or not to add nodes to the cluster. Returns the number of nodes
        to add.
        """
        num_nodes = len(self._cluster.nodes)
        if num_nodes >= self.max_nodes:
            log.info("Not adding nodes: already at or above maximum (%d)" %
                     self.max_nodes)
            return
        queued_jobs = self.stat.get_queued_jobs()
        if not queued_jobs and num_nodes >= self.min_nodes:
            log.info("Not adding nodes: at or above minimum nodes "
                     "and no queued jobs...")
            return
        total_slots = self.stat.count_total_slots()
        if not self.has_cluster_stabilized() and total_slots > 0:
            return
        running_jobs = self.stat.get_running_jobs()
        used_slots = sum([int(j['slots']) for j in running_jobs])
        qw_slots = sum([int(j['slots']) for j in queued_jobs])
        slots_per_host = self.stat.slots_per_host()
        avail_slots = total_slots - used_slots
        need_to_add = 0
        if num_nodes < self.min_nodes:
            log.info("Adding node: below minimum (%d)" % self.min_nodes)
            need_to_add = self.min_nodes - num_nodes
        elif total_slots == 0:
            # no slots, add one now
            need_to_add = 1
        elif qw_slots > avail_slots:
            log.info("Queued jobs need more slots (%d) than available (%d)" %
                     (qw_slots, avail_slots))
            oldest_job_dt = self.stat.oldest_queued_job_age()
            now = self.get_remote_time()
            age_delta = now - oldest_job_dt
            if age_delta.seconds > self.longest_allowed_queue_time:
                log.info("A job has been waiting for %d seconds "
                         "longer than max: %d" %
                         (age_delta.seconds, self.longest_allowed_queue_time))
                if slots_per_host != 0:
                    need_to_add = qw_slots / slots_per_host
                else:
                    need_to_add = 1
            else:
                log.info("No queued jobs older than %d seconds" %
                         self.longest_allowed_queue_time)
        max_add = self.max_nodes - len(self._cluster.running_nodes)
        need_to_add = min(self.add_nodes_per_iteration, need_to_add, max_add)
        if need_to_add > 0:
            log.warn("Adding %d nodes at %s" %
                     (need_to_add, str(utils.get_utc_now())))
            try:
                self._cluster.add_nodes(need_to_add)
                self.__last_cluster_mod_time = utils.get_utc_now()
                log.info("Done adding nodes at %s" %
                         str(self.__last_cluster_mod_time))
            except Exception:
                log.error("Failed to add new host", exc_info=True)

    def _eval_remove_node(self):
        """
        This function uses the sge stats to decide whether or not to
        remove a node from the cluster.
        """
        qlen = len(self.stat.get_queued_jobs())
        if qlen != 0:
            return
        if not self.has_cluster_stabilized():
            return
        num_nodes = len(self._cluster.nodes)
        if num_nodes <= self.min_nodes:
            log.info("Not removing nodes: already at or below minimum (%d)"
                     % self.min_nodes)
            return
        max_remove = num_nodes - self.min_nodes
        log.info("Looking for nodes to remove...")
        remove_nodes = self._find_nodes_for_removal(max_remove=max_remove)
        if not remove_nodes:
            log.info("No nodes can be removed at this time")
        for node in remove_nodes:
            if node.update() != "running":
                log.error("Node %s is already dead - not removing" %
                          node.alias)
                continue
            log.warn("Removing %s: %s (%s)" %
                     (node.alias, node.id, node.dns_name))
            try:
                self._cluster.remove_node(node)
                self.__last_cluster_mod_time = utils.get_utc_now()
            except Exception:
                log.error("Failed to remove node %s" % node.alias,
                          exc_info=True)

    def _eval_terminate_cluster(self):
        """
        This method determines whether to terminate the cluster based on the
        following conditions:
        1. Only the master node exists (no worker nodes)
        2. The master node is not running any SGE jobs
        3. The master node has been up for at least self.kill_after mins
        """
        if len(self._cluster.running_nodes) != 1:
            return False
        return self._should_remove(self._cluster.master_node)

    def _should_remove(self, node):
        """
        Determines whether a node is eligible to be removed based on:

        1. The node must not be running any SGE job
        2. The node must have been up for self.kill_after min past the hour
        """
        if self.stat.is_node_working(node):
            return False
        mins_up = self._minutes_uptime(node) % 60
        idle_msg = ("Idle node %s (%s) has been up for %d minutes past "
                    "the hour" % (node.alias, node.id, mins_up))
        if mins_up >= self.kill_after:
            log.info(idle_msg)
            return True
        else:
            log.debug(idle_msg)
            return False

    def _find_nodes_for_removal(self, max_remove=None):
        """
        This function returns one or more suitable worker nodes to remove from
        the cluster. The criteria for removal are:
        1. The node must be a worker node (ie not master)
        2. The node must not be running any SGE job
        3. The node must have been up for self.kill_after min past the hour

        If max_remove is specified up to max_remove nodes will be returned for
        removal.
        """
        remove_nodes = []
        for node in self._cluster.running_nodes:
            if max_remove is not None and len(remove_nodes) >= max_remove:
                return remove_nodes
            if node.is_master():
                continue
            if self._should_remove(node):
                remove_nodes.append(node)
        return remove_nodes

    def _minutes_uptime(self, node):
        """
        This function uses the node's launch_time to determine how many minutes
        this instance has been running. You can mod (%) the return value with
        60 to determine how many minutes into a billable hour this node has
        been running.
        """
        dt = utils.iso_to_datetime_tuple(node.launch_time)
        now = self.get_remote_time()
        timedelta = now - dt
        return timedelta.seconds / 60
