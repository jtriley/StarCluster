import os
import time
import datetime
import traceback
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
    jobstat_cachesize = 200
    hosts = []
    jobs = []
    jobstats = jobstat_cachesize * [None]
    max_job_id = 0
    _default_fields = ["JB_job_number", "state", "JB_submission_time",
                       "queue_name", "slots", "tasks"]

    @property
    def first_job_id(self):
        if not self.jobs:
            return
        return int(self.jobs[0]['JB_job_number'])

    @property
    def last_job_id(self):
        if not self.jobs:
            return
        return int(self.jobs[-1]['JB_job_number'])

    def parse_qhost(self, string):
        """
        this function parses qhost -xml output and makes a neat array
        takes in a string, so we can pipe in output from ssh.exec('qhost -xml')
        """
        self.hosts = []  # clear the old hosts
        doc = xml.dom.minidom.parseString(string)
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

    def parse_qstat(self, string, fields=None):
        """
        This method parses qstat -xml output and makes a neat array
        """
        if fields == None:
            fields = self._default_fields
        self.jobs = []  # clear the old jobs
        doc = xml.dom.minidom.parseString(string)
        for job in doc.getElementsByTagName("job_list"):
            jstate = job.getAttribute("state")
            hash = {"job_state": jstate}
            for tag in fields:
                es = job.getElementsByTagName(tag)
                for node in es:
                    for node2 in node.childNodes:
                        if node2.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                            hash[tag] = node2.data
            # grab the submit time on all jobs, the last job's val stays
            if 'tasks' in hash and hash['tasks'].find('-') > 0:
                self.job_multiply(hash)
            else:
                self.jobs.append(hash)
        return self.jobs

    def job_multiply(self, hash):
        """
        This function deals with sge jobs with a task range.  For example,
        'qsub -t 1-20:1' makes 20 jobs. self.jobs needs to represent that it is
        20 jobs instead of just 1.
        """
        sz_range = hash['tasks']
        dashpos = sz_range.find('-')
        colpos = sz_range.find(':')
        start = int(sz_range[0:dashpos])
        fin = int(sz_range[dashpos + 1:colpos])
        gran = int(sz_range[colpos + 1:len(sz_range)])
        log.debug("start = %d, fin = %d, granularity = %d, sz_range = %s" %
                  (start, fin, gran, sz_range))
        num_jobs = (fin - start) / gran
        log.debug("This job expands to %d tasks" % num_jobs)
        self.jobs.extend([hash] * num_jobs)

    def qacct_to_datetime_tuple(self, qacct):
        """
        Takes the SGE qacct formatted time and makes a datetime tuple
        format is:
        Tue Jul 13 16:24:03 2010
        """
        return datetime.datetime.strptime(qacct, "%a %b %d %H:%M:%S %Y")

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
                if qd != None:
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
            if j['job_state'] == u'pending':
                queued.append(j)
        return queued

    def count_hosts(self):
        """
        returns a count of the hosts in the cluster
        """
        #todo: throw an exception if hosts not initialized
        return len(self.hosts)

    def count_total_slots(self):
        """
        returns a count of total slots available in this cluser
        """
        slots = 0
        for h in self.hosts:
            if h['num_proc'] == '-':
                h['num_proc'] = 0
            slots = slots + int(h['num_proc'])
        return slots

    def slots_per_host(self):
        """
        returns the number of slots per host.
        If for some reason the cluster is inconsistent, this will return -1
        for example, if you have m1.large and m1.small in the same cluster
        """
        total = self.count_total_slots()
        if self.hosts[0][u'num_proc'] == '-':
            self.hosts[0][u'num_proc'] = 0
        single = int(self.hosts[0][u'num_proc'])
        if (total != (single * len(self.hosts))):
            log.error("ERROR: Number of slots not consistent across cluster")
            return -1
        return single

    def oldest_queued_job_age(self):
        """
        This returns the age of the oldest job in the queue
        """
        for j in self.jobs:
            if 'JB_submission_time' in j:
                st = j['JB_submission_time']
                dt = utils.iso_to_datetime_tuple(st)
                return dt
        #todo: throw a "no queued jobs" exception

    def is_node_working(self, node):
        """
        This function returns true if the node is currently working on a task,
        or false if the node is currently idle.
        """
        nodename = node.alias
        for j in self.jobs:
            if 'queue_name' in j:
                qn = j['queue_name']
                if qn.find(nodename) > 0:
                    log.debug("Node %s is working" % node.id)
                    return True
        log.debug("Node %s is IDLE" % node.id)
        return False

    def num_slots_for_job(self, job_id):
        """
        returns the number of slots requested for the given job id
        returns -1 if job_id is invalid
        """
        ujid = unicode(job_id)
        for j in self.jobs:
            if j['JB_job_number'] == ujid:
                return int(j['slots'])
        return -1

    def avg_job_duration(self):
        count = 0
        total_seconds = 0
        for job in self.jobstats:
            if job != None:
                delta = job['end'] - job['start']
                total_seconds = total_seconds + delta.seconds
                count = count + 1
        if count == 0:
            return 0
        else:
            return total_seconds / count

    def avg_wait_time(self):
        count = 0
        total_seconds = 0
        for job in self.jobstats:
            if job != None:
                delta = job['start'] - job['queued']
                total_seconds = total_seconds + delta.seconds
                count = count + 1
        if count == 0:
            return 0
        else:
            return total_seconds / count

    def on_first_job(self):
        """
        returns true if the cluster is processing the first job,
        False otherwise
        """
        if len(self.jobs) > 0 and self.jobs[0]['JB_job_number'] != u'1':
            log.info("ON THE FIRST JOB")
            return True
        return False

    def get_loads(self):
        """
        returns an array containing the loads on each host in cluster
        """
        loads = []
        for h in self.hosts:
            if h['load_avg'] == '-':
                h['load_avg'] = 0
            loads.append(h['load_avg'])
        return loads

    def _add(self, x, y):
        return float(x) + float(y)

    def get_all_stats(self):
        now = datetime.datetime.utcnow()
        bits = []
        #first field is the time
        bits.append(now)
        #second field is the number of hosts
        bits.append(self.count_hosts())
        #third field is # of running jobs
        bits.append(len(self.get_running_jobs()))
        #fourth field is # of queued jobs
        bits.append(len(self.get_queued_jobs()))
        #fifth field is total # slots
        bits.append(self.count_total_slots())
        #sixth field is average job duration
        bits.append(self.avg_job_duration())
        #seventh field is average job wait time
        bits.append(self.avg_wait_time())
        #last field is array of loads for hosts
        arr = self.get_loads()
        load_sum = float(reduce(self._add, arr))
        avg_load = load_sum / len(arr)
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

    The polling interval in seconds. recommended: 60-300. any more frequent is
    very wasteful. the polling loop with visualizer takes about 15 seconds.
    polling_interval = 60

    VERY IMPORTANT: Set this to the max nodes you're willing to have in your
    cluster. Try setting this to the default cluster size you'd ordinarily
    use.
    max_nodes = 5

    IMPORTANT: Set this to the longest time a job can wait before another host
    is added to the cluster to help. Recommended: 300-900 seconds (5-15 mins).
    Do not use a value less than 300 seconds because that is how long an
    instance will take to start up.
    longest_allowed_queue_time = 900

    Keep this at 1 - your master, for now.
    min_nodes = 1

    This would allow the master to be killed when the queue empties. UNTESTED.
    allow_master_kill = False

    How many nodes to add per iteration. Setting it > 1 opens up possibility
    of spending too much $$
    add_nodes_per_iteration = 1

    Kill an instance after it has been up for X minutes. Do not kill earlier,
    since you've already paid for that hour. (in mins)
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
                 min_nodes=1, allow_master_kill=False, plot_stats=False,
                 plot_output_dir=None, dump_stats=False, stats_file=None):
        self._cluster = None
        self._keep_polling = True
        self._visualizer = None
        self.__last_cluster_mod_time = datetime.datetime.utcnow()
        self.stat = None
        self.polling_interval = interval
        self.max_nodes = max_nodes
        self.longest_allowed_queue_time = wait_time
        self.add_nodes_per_iteration = add_pi
        self.kill_after = kill_after
        self.stabilization_time = stab
        self.lookback_window = lookback_win
        self.min_nodes = min_nodes
        self.allow_master_kill = allow_master_kill
        if self.longest_allowed_queue_time < 300:
            log.warn("The recommended wait_time should be >= 300 seconds "
                     "(it takes ~5 min to launch a new EC2 node)")
        self.dump_stats = dump_stats
        self.stats_file = stats_file
        self.plot_stats = plot_stats
        self.plot_output_dir = plot_output_dir
        if plot_stats:
            assert self.visualizer != None

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
        this function remotely executes 'date' on the master node
        and returns a datetime object with the master's time
        instead of fetching it from local machine, maybe inaccurate.
        """
        cl = self._cluster
        str = '\n'.join(cl.master_node.ssh.execute('date'))
        return datetime.datetime.strptime(str, "%a %b %d %H:%M:%S UTC %Y")

    def get_qatime(self, now):
        """
        this function takes the lookback window and creates a string
        representation of the past few hours, to feed to qacct to
        limit the data set qacct returns.
        """
        if self.stat.is_jobstats_empty():
            log.info("Loading full job history")
            temp_lookback_window = self.lookback_window * 60 * 60
        else:
            temp_lookback_window = self.polling_interval
        log.debug("getting past %d seconds worth of job history" %
                  temp_lookback_window)
        now = now - datetime.timedelta(seconds=temp_lookback_window + 1)
        str = now.strftime("%Y%m%d%H%M")
        return str

    #@print_timing
    def get_stats(self):
        """
        this function will ssh to the SGE master and get load & queue stats.
        it will feed these stats to SGEStats, which parses the XML.
        it will return two arrays: one of hosts, each host has a hash with its
        host information inside. The job array contains a hash for every job,
        containing statistics about the job name, priority, etc.
        """
        log.debug("starting get_stats")
        master = self._cluster.master_node
        self.stat = SGEStats()

        qhostxml = ""
        qstatxml = ""
        qacct = ""
        try:
            now = self.get_remote_time()
            qatime = self.get_qatime(now)
            qacct_cmd = 'qacct -j -b ' + qatime
            qstat_cmd = 'qstat -q all.q -u \"*\" -xml'
            qhostxml = '\n'.join(master.ssh.execute('qhost -xml',
                                                    log_output=True,
                                                    source_profile=True))
            qstatxml = '\n'.join(master.ssh.execute(qstat_cmd,
                                                    log_output=True,
                                                    source_profile=True))
            qacct = '\n'.join(master.ssh.execute(qacct_cmd, log_output=True,
                                                 ignore_exit_status=True,
                                                 source_profile=True))
        except Exception, e:
            log.error("Error occurred getting SGE stats via ssh. "
                      "Cluster terminated?")
            log.error(e)
            return -1
        log.debug("sizes: qhost: %d, qstat: %d, qacct: %d" %
                  (len(qhostxml), len(qstatxml), len(qacct)))
        self.stat.parse_qhost(qhostxml)
        self.stat.parse_qstat(qstatxml)
        self.stat.parse_qacct(qacct, now)

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
        log.info("Starting load balancer...\n")
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
            if self.get_stats() == -1:
                log.error("Failed to get stats. LoadBalancer is terminating")
                return
            log.info("Cluster size: %d" % len(self.stat.hosts), extra=raw)
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
                     self.__last_cluster_mod_time.strftime("%Y-%m-%d %X"),
                     extra=dict(__raw__=True))
            #evaluate if nodes need to be added
            self._eval_add_node()
            #evaluate if nodes need to be removed
            self._eval_remove_node()
            if self.dump_stats or self.plot_stats:
                self.stat.write_stats_to_csv(self.stats_file)
            #call the visualizer
            if self.plot_stats:
                try:
                    self.visualizer.graph_all()
                except IOError, e:
                    raise exception.BaseException(str(e))
            #sleep for the specified number of seconds
            log.info("Sleeping...(looping again in %d secs)\n" %
                     self.polling_interval)
            time.sleep(self.polling_interval)

    def has_cluster_stabilized(self):
        now = datetime.datetime.utcnow()
        elapsed = (now - self.__last_cluster_mod_time).seconds
        is_stabilized = not (elapsed < self.stabilization_time)
        if not is_stabilized:
            log.info("Cluster was modified less than %d seconds ago" %
                     self.stabilization_time)
            log.info("Waiting for cluster to stabilize...")
        return is_stabilized

    def _eval_add_node(self):
        """
        This function uses the metrics available to it to decide whether to
        add a new node to the cluster or not. It isn't able to add a node yet.
        TODO: See if the recent jobs have taken more than 5 minutes (how
        long it takes to start an instance)
        """
        need_to_add = 0
        if len(self.stat.hosts) >= self.max_nodes:
            log.info("Not adding nodes: already at or above maximum (%d)" %
                     self.max_nodes)
            return 0
        qlen = len(self.stat.get_queued_jobs())
        sph = self.stat.slots_per_host()
        ts = self.stat.count_total_slots()
        #calculate job duration
        avg_duration = self.stat.avg_job_duration()
        #calculate estimated time to completion
        ettc = avg_duration * qlen / len(self.stat.hosts)
        if qlen > ts:
            if not self.has_cluster_stabilized():
                return 0
            #there are more jobs queued than will be consumed with one
            #cycle of job processing from all nodes
            oldest_job_dt = self.stat.oldest_queued_job_age()
            now = self.get_remote_time()
            age_delta = now - oldest_job_dt
            if age_delta.seconds > self.longest_allowed_queue_time:
                log.info("A job has been waiting for %d sec, longer than "
                         "max %d" % (age_delta.seconds,
                                      self.longest_allowed_queue_time))
                need_to_add = qlen / sph
                if ettc < 600 and not self.stat.on_first_job():
                    log.warn("There is a possibility that the job queue is"
                             " shorter than 10 minutes in duration")
                    #need_to_add = 0
        max_add = self.max_nodes - len(self.stat.hosts)
        need_to_add = min(self.add_nodes_per_iteration, need_to_add, max_add)
        if need_to_add > 0:
            log.info("*** ADDING %d NODES at %s" %
                     (need_to_add, str(datetime.datetime.utcnow())))
            try:
                self._cluster.add_nodes(need_to_add)
            except Exception:
                log.error("Failed to add new host")
                log.debug(traceback.format_exc())
                return -1
            self.__last_cluster_mod_time = datetime.datetime.utcnow()
            log.info("Done adding nodes at %s" %
                     str(datetime.datetime.utcnow()))
        return need_to_add

    def _eval_remove_node(self):
        """
        This function uses the sge stats to decide whether or not to
        remove a node from the cluster.
        """
        qlen = len(self.stat.get_queued_jobs())
        if qlen == 0:
            if not self.has_cluster_stabilized():
                return 0
            #if at 0, remove all nodes but master
            if len(self.stat.hosts) > self.min_nodes:
                log.info("Checking to remove a node...")
                to_kill = self._find_node_for_removal()
                if not to_kill:
                    log.info("No nodes can be killed at this time")
                #kill the nodes returned
                for n in to_kill:
                    if n.update() == "running":
                        log.info("***REMOVING NODE: %s (%s)" % (n.id,
                                                                n.dns_name))
                        try:
                            self._cluster.remove_node(n)
                        except Exception:
                            log.error("Failed to remove node %s" % n.alias)
                            log.debug(traceback.format_exc())
                            return -1
                        #successfully removed node
                        now = datetime.datetime.utcnow()
                        self.__last_cluster_mod_time = now
                    else:
                        log.error("Trying to kill dead node %s" % n.alias)
            else:
                log.info("Not removing nodes: already at or below minimum (%d)"
                         % self.min_nodes)

    def _find_node_for_removal(self):
        """
        This function will find a suitable node to remove from the cluster.
        The criteria for removal are:
        1. The node must not be running any SGE job
        2. The node must have been up for 50-60 minutes past its start time
        3. The node must not be the master, or allow_master_kill=True
        """
        nodes = self._cluster.running_nodes
        to_rem = []
        for node in nodes:
            if not self.allow_master_kill and node.is_master():
                log.debug("not removing master node")
                continue
            is_working = self.stat.is_node_working(node)
            mins_up = self._minutes_uptime(node) % 60
            if not is_working:
                log.info("Idle Node %s (%s) has been up for %d minutes "
                         "past the hour" % (node.id, node.alias, mins_up))
            if self.polling_interval > 300:
                self.kill_after = max(45,
                                      60 - (2 * self.polling_interval / 60))
            if not is_working and mins_up >= self.kill_after:
                to_rem.append(node)
        return to_rem

    def _minutes_uptime(self, node):
        """
        this function uses data available to boto to determine
        how many total minutes this instance has been running. you can
        mod (%) the return value with 60 to determine how many minutes
        into a billable hour this node has been running.
        """
        dt = utils.iso_to_datetime_tuple(node.launch_time)
        now = self.get_remote_time()
        timedelta = now - dt
        return timedelta.seconds / 60
