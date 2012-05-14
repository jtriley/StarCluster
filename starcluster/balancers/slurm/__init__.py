"""
SLURM Load Balancer for StarCluster
Author: Jharrod LaFon, OpenEye Scientific Software
http://www.eyesopen.com
"""

import time
import sys
import datetime
import traceback
from starcluster import exception
from starcluster.logger import log
from starcluster.balancers import LoadBalancer
from starcluster.utils import print_timing
from starcluster.utils import iso_to_datetime_tuple
from starcluster.exception import SSHError
from ssh import SFTPError


class SlurmLoadBalancer(LoadBalancer):
    """
    This class is a load balancer for SLURM.
    """


    def __init__(self, interval=60, max_nodes=None, wait_time=300,
                 add_pi=1, kill_after=45, stab=180, lookback_win=3,
                 min_nodes=1, kill_cluster=False, plot_stats=False,
                 plot_output_dir=None, dump_stats=False,
                 stats_file=None):
        super(SlurmLoadBalancer, self).__init__()
        self._cluster = None
        self._keep_polling = True
        self._visualizer = None
        self.__last_cluster_mod_time = datetime.datetime.utcnow()
        self.state = None
        self.polling_interval = min(interval, 300)
        self.kill_after = kill_after
        self.max_nodes = max_nodes
        self.longest_allowed_queue_time = max(300, wait_time)
        self.add_nodes_per_iteration = add_pi
        self.stabilization_time = stab
        self.kill_cluster = kill_cluster
        self.min_nodes = min_nodes if not kill_cluster else 0
        self._pending_operation = False

    def _format_info_log_message(self, prefix, suffix,fill=".",width=76):
        """
        Format a message and send to info
        prefix.....suffix (width chars wide)
        """
        log.info(str(prefix) + str(fill)*(width-len(str(prefix)+str(suffix)))+str(suffix))

    @property
    def pending_operation(self):
        """
        Returns true if there is a pending operation (adding or removing node(s))
        """
        return self._pending_operation

    def run(self, cluster):
        """
        Function to loop forever, bringing balance to the force,
        and the cluster.
        """
        self._cluster = cluster

        # Initialize state
        self.state = SlurmState(cluster)

        # Make sure that max_nodes has a valid value
        if self.max_nodes is None:
            self.max_nodes = cluster.cluster_size

        # Make sure the cluster is running
        if not cluster.is_cluster_up():
            raise exception.ClusterNotRunning(cluster.cluster_tag)

        # Print the header
        self._print_header()

        # Balance loop
        while self._keep_polling:
            try:
                self._balance_loop()
            except SlurmLoadBalancerError, e:
                log.error(str(e))
                sys.exit()
            except KeyboardInterrupt:
                if self.pending_operation:
                    log.warn("Load balancer interrupted while modifying the cluster."
                    " The operation may or may not be complete.")
                else:
                    log.warn("Load balancer terminated.  ")
                sys.exit()

    def _print_header(self):
        log.info("Starting load balancer (Use ctrl-c to exit)")
        self._format_info_log_message("Maximum cluster size:", self.max_nodes)
        self._format_info_log_message("Minimum cluster size:", self.min_nodes)
        self._format_info_log_message("Cluster growth rate:", "%d nodes/iteration" % \
                 self.add_nodes_per_iteration)

    def _print_stats(self):
        """
        Print out job statistics
        """
        log.info("\n")
        self._format_info_log_message("Cluster Size:",len(self.state.nodes))
        self._format_info_log_message("Slots per host:",self.state.slots_per_host)
        self._format_info_log_message("Queued jobs:",len(self.state.queued_jobs))
        self._format_info_log_message("Pending jobs:",len(self.state.pending_jobs))
        self._format_info_log_message("Running jobs:",len(self.state.running_jobs))
        self._format_info_log_message("Completed jobs:",len(self.state.completed_jobs))
        if self.state.has_pending_jobs:
            self._format_info_log_message("Oldest pending job:", \
                      self.state.oldest_pending_job_age)
        self._format_info_log_message("Average job duration per node:",  "%6.2fs" \
                 % self.state.average_job_duration)
        self._format_info_log_message("Average job wait time:", "%6.2fs" \
                 % self.state.average_job_wait)
        self._format_info_log_message("Last cluster modification time:",
             self.__last_cluster_mod_time.strftime("%Y-%m-%d %X UTC"))
        self._format_info_log_message("Estimated Time to Completion:", "%.2fs" \
                 % self.state.est_time_to_completion)

    def _balance_loop(self):
        """
        Wrapper for balance loop
        """
        self._inner_balance_loop()
        time.sleep(self.polling_interval)

    @print_timing("Cluster balancing routine")
    def _inner_balance_loop(self):
        """
        Main loop of the balancer.  Every cycle it gets
        the state of the cluster and decides whether to
        add, remove nodes - or do nothing.
        """

        # Make sure the cluster is up
        if not self._cluster.is_cluster_up():
            log.info("Waiting for all nodes to come up...")
            time.sleep(self.polling_interval)
            return

        # Print the current state
        self._print_stats()

        # Only check to see if we should add a node if there
        # are pending jobs
        if self.state.has_pending_jobs:
            self._eval_add_node()

        # If there are no pending jobs, check to see if we
        # can remove a node
        else:
            self._eval_remove_node()

        # If the user specified that the cluster can be
        # killed, check for that condition
        if self.kill_cluster:
            if self._eval_terminate_cluster():
                log.info("Terminating cluster and exiting...")
                self._cluster.terminate_cluster()
                sys.exit(0)
        log.info("Sleeping...(looping again in %d secs)" %
                self.polling_interval)

    def has_cluster_stabilized(self):
        """
        Returns True if the cluster hasn't been
        modified in the last self.stabilization_time
        seconds, false otherwise.
        """
        now = datetime.datetime.utcnow()
        elapsed = (now - self.__last_cluster_mod_time).seconds
        is_stabilized = not (elapsed < self.stabilization_time)
        if not is_stabilized:
            log.info("Cluster was modified less than %d seconds ago" %
                     self.stabilization_time)
        return is_stabilized

    def _eval_add_node(self):
        """
        Decides whether or not to add a new node.
        A node is added if all the conditions below are true:
           -There are pending jobs in the queue
           -There are fewer than the maxium allowed nodes allocated
        Up to add_nodes_per_iteration will be added.
        """

        if len(self.state.nodes) >= self.max_nodes:
            log.info("Not adding nodes: already at or above maximum (%d)" %
                self.max_nodes)

        # How long has the oldest job been waiting?
        if self.state.oldest_pending_job_age \
           > self.longest_allowed_queue_time:
            # Longer than X minutes

            # Are there so many jobs that the queue will have items
            #    after 5 minutes?
            # (or jobs pending but not running if we
            # are not computing on the master node)
            if self.state.est_time_to_completion > 300 or \
                (self.state.has_pending_jobs and \
                 not self.state.has_running_jobs):

                # Was the last cluster modification more recent
                #   than 3 minutes ago?
                if self.has_cluster_stabilized():
                    self._add_node()
                else:
                    log.info("Cluster not stabilized, not adding node.")
                    return
            else:
                # The queue will (probably) not have work after 5 minutes
                log.info(
                    "Est. time to completion < 5 minutes, not adding nodes.")
                return
        else:
            # Shorter than X minutes
            log.info(
                "Oldest job has not waited at least %s seconds, not adding nodes." \
                % self.longest_allowed_queue_time)
            return

    def _add_node(self):
        """
        Adds nodes to the cluster, the minimum of
        {add_nodes_per_iteration, nodes_needed_for_all_jobs,
        max_nodes - (number of running nodes)}
        """
        qty_needed = min(
                        self.add_nodes_per_iteration,
                        self.state._nodes_needed_for_all_jobs(),
                        self.max_nodes - len(self._cluster.running_nodes))

        # If qty_need is nonzero, we can add nodes
        if qty_needed > 0:
            log.warn("Adding %d nodes at %s" % (
                     qty_needed,
                     str(datetime.datetime.utcnow())))
            self.__last_cluster_mod_time = datetime.datetime.utcnow()
            self._pending_operation = True
            self._cluster.add_nodes(qty_needed)
            self._pending_operation = False
            self.__cluster_mode_time = datetime.datetime.utcnow()
            log.info("Done adding nodes at %s" %
               str(datetime.datetime.utcnow()))
        return

    def _eval_remove_node(self):
        """
        Decides whether or not to remove a node.
        Implemented to match the flowchart at:
        http://web.mit.edu/star/cluster/docs/latest/manual/load_balancer.html
        """

        # Was the last cluster modification more recent than 3 minutes?
        if not self.has_cluster_stabilized():
            log.info("Cluster not stabilized yet, not removing nodes.")
            return

        # Nodes should be removed
        if self.state.has_pending_jobs:
            return

        # Don't got below minimum
        if len(self.state.nodes) <= self.min_nodes:
            log.info("Not removing nodes: already at or below minimum (%d)"
                % self.min_nodes)
            return

        # Are any nodes idle?
        #    The list returned will not include nodes
        #    that have not been up at least X minutes passed
        #    the hour
        candidate_list = self._find_nodes_for_removal()
        if not len(candidate_list):
            log.info("Cannot remove nodes, none are eligible.")
            return

        for node in candidate_list:
            # Make sure it's not already dead.
            if node.update() != "running":
                log.error("Node %s is already dead - not removing" %
                    node.alias)
                continue
            log.warn("Removing %s: %s (%s)" %
                (node.alias, node.id, node.dns_name))
            try:
                self._pending_operation = True
                self._cluster.remove_node(node)
                self._pending_operation = False
                self.__last_cluster_mod_time = datetime.datetime.utcnow()
            except Exception:
                log.error("Failed to remove node %s" % node.alias)
                log.debug(traceback.format_exc())

    def _eval_terminate_cluster(self):
        """
        Decides whether or not to terminate the cluster.
        """
        if len(self._cluster.running_nodes) != 1:
            return False
        return self._evaluate_node_for_removal(self._cluster.master_node)

    def _evaluate_node_for_removal(self, node):
        """
        Evaluates an individual node for removal.

        Returns False if the node is busy, or hasn't
        been up at least self.kill_after minutes after
        the top of the hour.

        Returns True otherwise.
        """
        if self._node_is_busy(node):
            return False
        minutes = self._minutes_uptime(node) % 60
        log.info("Idle node %s (%s) has been up for %d "
                 "minutes past the hour." %
                 (node.alias, node.id, minutes))
        if minutes >= self.kill_after:
            return True
        else:
            return False

    def _minutes_uptime(self, node):
        """
        Returns the uptime of the node in minutes,
        modulo one hour
        """
        return (self.state.remote_time - \
            iso_to_datetime_tuple(node.launch_time)).seconds \
            / 60

    def _node_is_busy(self, node):
        """
        Returns True is a node is busy with a job.
        False, otherwise.
        """
        for job in self.state.queued_jobs:
            if node.alias in job.nodelist.split(','):
                return True
        return False

    def _find_nodes_for_removal(self):
        """
        Looks for nodes that can be removed from the cluster.
        """
        self.max_remove = len(self.state.nodes) - self.min_nodes
        list = []
        for node in self._cluster.running_nodes:
            if len(list) >= self.max_remove:
                return list
            if node.is_master():
                continue
            if self._evaluate_node_for_removal(node):
                list.append(node)
        return list


class cachedproperty(object):
    """ Class decorator to cache a property for
        a given amount of time.
        The property will be queried again after if
        a __get__ is called after it has expired.
    """
    def __init__(self, timeout=10):
        self.timeout = timeout
        self._cache = {}

    def __call__(self, func):
        self.func = func
        return self

    def __get__(self, obj, objcls):
        if obj not in self._cache or \
           (self.timeout and time.time() - self._cache[obj][1] > self.timeout):
            self._cache[obj] = (self.func(obj), time.time())
        return self._cache[obj][0]


class SlurmJob(object):
    """
    Class representing a SLURM job
    """
    def __init__(self, **kwargs):
        self.update(**kwargs)

    def __repr__(self):
        return "<SlurmJob: %6s User: %10s Submit: %s Start: %s End: %s>" % \
               (self.jobid,
                self.user,
                self.submit,
                self.start,
                self.end)

    def __getattr__(self, name):
        """
        Check to see if this job has the specified attribute,
        without failing
        """
        # Note that if this gets called, getting attributes failed
        # to find the desired attribute in any of the normal places
        return 'N/A'

    def update(self, **kwargs):
        """
        Updates a job's attributes
        """
        for k in kwargs:
            if isinstance(kwargs[k], str):
                setattr(self, k, kwargs[k].lower())
            else:
                setattr(self, k, kwargs[k])


class SlurmState(object):
    """
    Holds SLURM state
    """
    # Fields we want squeue to print
    squeue_fields = [
        "nodes",
        "end_time",
        "jobid",
        "name",
        "timelimit",
        "time_left",
        "time",
        "nodelist",
        "reason",
        "start_time",
        "state"]

    #    The field specifications available include:
    #
    #    %a  Account associated with the job
    #
    #    %b  Time at which the job began execution
    #
    #    %c  Minimum number of CPUs (processors) per node
    #    requested by the job.  This reports the value of
    #    the srun --mincpus option with a default value of
    #    zero.
    #
    #    %C  Number of CPUs (processors) requested to the job or
    #    job step.  This reports the value of the srun
    #    --ntasks option with a default value of zero.
    #
    #    %d  Minimum size of temporary disk space (in MB)
    #    requested by the job.
    #
    #    %D  Number of nodes allocated to the job or the minimum
    #    number of nodes required by a pending job. The
    #    actual number of nodes allocated to a pending job
    #    may exceed this number of the job specified a node
    #    range count or the cluster contains nodes with
    #    varying processor counts.
    #
    #    %e  Time at which the job ended or is expected to end
    #    (based upon its time limit)
    #
    #    %E  Job dependency. This job will not begin execution
    #    until the dependent job completes.  A value of zero
    #    implies this job has no dependencies.
    #
    #    %f  Features required by the job
    #
    #    %g  Group name
    #
    #    %G  Group ID
    #
    #    %h  Can the nodes allocated to the job be shared with
    #    other jobs
    #
    #    %i  Job or job step id
    #
    #    %j  Job or job step name
    #
    #    %l  Time limit of the job in
    #    days-hours:minutes:seconds. The value may be
    #    "NOT_SET" if not yet established or "UNLIMITED" for
    #    no limit.
    #
    #    %m  Minimum size of memory (in MB) requested by the job
    #
    #    %M  Time used by the job or job step in
    #    days-hours:minutes:seconds. The days and hours are
    #    printed only as needed.  For job steps this field
    #    shows the elapsed time since execution began and
    #    thus will be inaccurate for job steps which have
    #    been suspended.
    #
    #    %n  List of node names explicitly requested by the job
    #
    #    %N  List of nodes allocated to the job or job step. In
    #    the case of a COMPLETING job, the list of nodes
    #    will comprise only those nodes that have not yet
    #    been returned to service. This may result in the
    #    node count being greater than the number of listed
    #    nodes.
    #
    #    %o  Minimum number of nodes requested by the job.
    #
    #    %O  Are contiguous nodes requested by the job
    #
    #    %p  Priority of the job (converted to a floating point
    #    number between 0.0 and 1.0
    #
    #    %P  Partition of the job or job step
    #
    #    %r  The reason a job is waiting for execution.  See the
    #    JOB REASON CODES section below for more
    #    information.
    #    %E  Job dependency. This job will not begin execution
    #        until the dependent job completes.  A value of zero
    #        implies this job has no dependencies.
    #
    #    %f  Features required by the job
    #
    #    %g  Group name
    #
    #    %G  Group ID
    #
    #    %h  Can the nodes allocated to the job be shared with
    #    other jobs
    #
    #    %i  Job or job step id
    #
    #    %j  Job or job step name
    #
    #    %l  Time limit of the job in
    #    days-hours:minutes:seconds. The value may be
    #    "NOT_SET" if not yet established or "UNLIMITED" for
    #    no limit.
    #
    #    %m  Minimum size of memory (in MB) requested by the job
    #
    #    %M  Time used by the job or job step in
    #    days-hours:minutes:seconds. The days and hours are
    #    printed only as needed.  For job steps this field
    #    shows the elapsed time since execution began and
    #    thus will be inaccurate for job steps which have
    #    been suspended.
    #
    #    %n  List of node names explicitly requested by the job
    #
    #    %N  List of nodes allocated to the job or job step. In
    #    the case of a COMPLETING job, the list of nodes
    #    will comprise only those nodes that have not yet
    #    been returned to service. This may result in the
    #    node count being greater than the number of listed
    #    nodes.
    #
    #    %o  Minimum number of nodes requested by the job.
    #
    #    %O  Are contiguous nodes requested by the job
    #
    #    %p  Priority of the job (converted to a floating point
    #    number between 0.0 and 1.0
    #
    #    %P  Partition of the job or job step
    #
    #    %r  The reason a job is waiting for execution.  See the
    #    JOB REASON CODES section below for more
    #    information.

    squeue_command = "squeue -h --format=\"%D %e %i %j %l %L %M %N %r %S %t\" "
    scontrol_command = "scontrol -o show job -a"
    sacct_command = \
        "sacct -P -s CD --format=jobid,submit,start,end,nnodes,user " + \
        "| egrep -v '\.batch'"
    slurm_time_format = "%Y-%m-%dT%H:%M:%S"
    slurm_replacement_fields = \
        [('submittime','submit'),
         ('starttime', 'start'),
         ('endtime', 'end'),
         ('userid','user'),
         ('numnodes','nnodes')]
    remote_exceptions = (SFTPError, SSHError, IOError)

    def __init__(self, cluster):
        self._nodes = None
        self._jobs = None
        self._completed_jobs = None
        self._pending_jobs = None
        self._running_jobs = None
        self._slots_per_host = None
        self._cluster = cluster
        self._master = None
        self._remote_time = None
        self._average_job_wait = None
        self._average_job_duration = None
        self._oldest_queued_job_age = None
        self._oldest_pending_job_age = None
        self._est_ttc = None

    @property
    def remote_time(self):
        """
        Returns cluster time as a datetime object
        """
        self._set_remote_time()
        return self._remote_time

    @property
    def master(self):
        """
        Returns master node object
        """
        self._master = self._cluster.master_node
        return self._master

    @cachedproperty(30)
    def running_jobs(self):
        """
        Returns list of running SlurmJobs
        """
        self._set_running_jobs()
        return self._running_jobs

    @cachedproperty(30)
    def pending_jobs(self):
        """
        Returns the list of queued SlurmJobs
        """
        self._set_pending_jobs()
        return self._pending_jobs

    @cachedproperty(30)
    def nodes(self):
        """
        Returns list of cluster nodes
        """
        self._nodes = self._cluster.nodes
        return self._nodes

    @cachedproperty(30)
    def slots_per_host(self):
        """
        Returns number of execution slots per host
        """
        self._set_slot_info()
        return self._slots_per_host

    @cachedproperty(30)
    def queued_jobs(self):
        """
        Returns list of queued jobs
        """
        self._set_queued_jobs()
        self._set_jobs_details()
        return self._jobs

    @cachedproperty(30)
    def completed_jobs(self):
        """
        Returns list of completed jobs
        """
        self._set_completed_jobs()
        return self._completed_jobs

    @cachedproperty(30)
    def average_job_wait(self):
        """
        Returns average job wait time
        """
        self._set_average_job_wait()
        return self._average_job_wait

    @cachedproperty(30)
    def has_running_jobs(self):
        """
        Returns True if there are running jobs
        """
        return len(self.running_jobs) > 0

    @cachedproperty(30)
    def has_pending_jobs(self):
        """
        Returns True if there are pending jobs
        in the queue.
        """
        return len(self.pending_jobs) > 0

    @cachedproperty(30)
    def has_queued_jobs(self):
        """
        Returns True if there are queued jobs
        """
        return len(self.queued_jobs) > 0

    @cachedproperty(30)
    def oldest_pending_job_age(self):
        """
        Returns oldest pending job age (seconds)
        """
        self._set_oldest_pending_job_age()
        return self._oldest_pending_job_age

    @cachedproperty(30)
    def oldest_queued_job_age(self):
        """
        Returns oldest queued job age (seconds)
        """
        self._set_oldest_queued_job_age()
        return self._oldest_queued_job_age

    @cachedproperty(30)
    def average_job_duration(self):
        """
        Returns average job duration per node (seconds)
        """
        self._set_average_job_duration()
        return self._average_job_duration

    @cachedproperty(30)
    def est_time_to_completion(self):
        """
        Returns the estimated time to completion of
        all queued jobs (seconds)
        """
        self._set_est_ttc()
        return self._est_ttc

    def _set_average_job_duration(self):
        """
        Calculates and returns the average job duration.
        """
        log.debug("Setting average job duration")
        sum = 0
        count = 0
        if not len(self.completed_jobs + self.running_jobs):
            self._average_job_duration = 0
        else:
            # Average job running times
            for job in self.completed_jobs:
                try:
                    sum += ((self._str_to_date(job.end) \
                        - self._str_to_date(job.start)).seconds) \
                         / float(job.nnodes)
                    count += 1
                except KeyError:
                    continue
            for job in self.running_jobs:
                sum += ((self.remote_time \
                        - self._str_to_date(job.start)).seconds) / float(job.nnodes)
                count += 1
            self._average_job_duration = sum / float(count)

    def _set_oldest_pending_job_age(self):
        """
        Set age of oldest pending job (seconds)
        """
        log.debug("Setting oldest pending job age")
        if not self.has_pending_jobs:
            self._oldest_pending_job_age = 0
        else:
            self._oldest_pending_job_age = \
                self._get_remote_time_epoch() - min(
                    [self._get_job_submit_time_epoch(job)
                     for job in self.pending_jobs])

    def _set_oldest_queued_job_age(self):
        """
        Set age of oldest queued job (seconds)
        """
        log.debug("Setting oldest queued job age")
        if not self.has_queued_jobs:
            self._oldest_queued_job_age = 0
        else:
            self._oldest_queued_job_age = \
                self._get_remote_time_epoch() - min(
                    [self._get_job_submit_time_epoch(job) \
                     for job in self.queued_jobs])

    def _set_average_job_wait(self):
        """
        Set average job wait time (in pending state)
        """
        log.debug("Setting average job wait")
        sum = 0
        if not len(self.completed_jobs + self.pending_jobs):
            self._average_job_wait = 0
        else:
            count = 0
            for job in self.completed_jobs:
                sum += (self._str_to_date(job.start) \
                        - self._str_to_date(job.submit)).seconds
                count += 1
            for job in self.pending_jobs:
                sum += (self._remote_time \
                        - self._str_to_date(job.submit)).seconds
                count += 1
            self._average_job_wait = sum / float(count)

    def _set_running_jobs(self):
        """
        Set the list of running jobs
        """
        log.debug("Setting running jobs list")
        self._running_jobs = filter(
            lambda job: job.jobstate == 'running', self.queued_jobs)
        if self._running_jobs is None:
            self._running_jobs = []

    def _set_pending_jobs(self):
        """
        Set the list of pending jobs
        """
        log.debug("Setting pending jobs list")
        self._pending_jobs = filter(
            lambda job: job.jobstate == 'pending', self.queued_jobs)
        if self._pending_jobs is None:
            self._pending_jobs = []

    def _set_queued_jobs(self):
        """
        Set the list of queued jobs (all states that show up in squeue)
        """
        log.debug("Setting queued jobs list")
        try:
            output = self.master.ssh.execute(self.squeue_command)
        except self.remote_exceptions, e:
            raise SlurmControllerError(
                "Unable to get list of queued jobs from SLURM: " + str(e))
        self._set_jobs_from_squeue(output)

    def _set_jobs_from_squeue(self, output):
        """
        Parses output from squeue (queued jobs)
        """
        log.debug("Parsing squeue output")
        jobs = []
        for line in output:
            job_dict = self._parse_squeue_line(line)
            jobs.append(SlurmJob(**job_dict))
        self._jobs = jobs

    def _parse_squeue_line(self, line):
        """
        Parses the output from one line of squeue
        """
        log.debug("Parsing one line of squeue output")
        job = {}
        values = line.split(' ')
        for field in self.squeue_fields:
            job[field.lower()] = values.pop(0)
        return job

    def _set_slot_info(self):
        """
        Sets the number of slots per node from
        the cluster.
        """
        log.debug("Setting slot info")
        sinfo_slots_command = "sinfo -e -h -t idle,alloc -o \"%c %D\""
        try:
            output = self.master.ssh.execute(
                sinfo_slots_command,
                raise_on_failure=True)
        except self.remote_exceptions, e:
            raise SlurmControllerError(
                "Unable to get SLURM compute node slot information: " + str(e))
        if not len(output):
            log.warn("Unable to determine slots per host, using value of 1")
            slots_per_host = 1
        else:
            slots_per_host = int(output[0].split(' ')[0])
        self._slots_per_host = slots_per_host

    def _set_completed_jobs(self):
        """
        Gets the list of completed jobs
        from the cluster.
        """
        log.debug("Setting completed jobs list")
        try:
            output = self.master.ssh.execute(self.sacct_command)
        except self.remote_exceptions, e:
            raise SlurmControllerError(
                "Unable to get list of completed jobs from SLURM: " + str(e))
        self._set_completed_jobs_from_sacct(output)

    def _set_completed_jobs_from_sacct(self, output):
        """
        Parses output from sacct (completed jobs)
        """
        log.debug("Parsing sacct output")
        completed_jobs = []
        fields = output[0].split('|')
        for line in output[1:]:
            completed_job_dict = self._parse_sacct_line(fields, line)
            completed_jobs.append(SlurmJob(**completed_job_dict))
        self._completed_jobs = completed_jobs

    def _parse_sacct_line(self, fields, line):
        """
        Parses sacct output:
        sacct -s CD --format=jobid,submit,start,end,nnodes
        """
        log.debug("Parsing line of sacct output")
        job = {}
        values = line.split('|')
        for field in fields:
            try:
                job[field.lower()] = values.pop(0)
            except IndexError:
                break
        return job

    def _get_job_by_id(self, jobidnum):
        """
        Return the job by id number, or a new job
        created with the given id number
        """
        log.debug("Looking up job by id " + str(jobidnum))
        for job in self._jobs:
            if job.jobid == jobidnum:
                return job
        return SlurmJob(jobid=jobidnum)

    def _set_jobs_details(self):
        """
        Get the details for each job
        """
        log.debug("Setting job details")
        try:
            output = self.master.ssh.execute(self.scontrol_command)
        except self.remote_exceptions, e:
            raise SlurmControllerError(
                "Unable to get job details from SLURM: " + str(e))
        for line in output:
            jobinfo = self._get_job_details(line)
            if 'jobid' in jobinfo:
                self._get_job_by_id(jobinfo['jobid']).update(**jobinfo)

    def _get_job_dict(self, job_list, job):
        """
        Returns the dictionary representing
        one job.
        """
        log.debug("Getting job dictionary")
        for j in job_list:
            if j['jobid'] == job['jobid']:
                return j
        return {}

    def _get_job_details(self, output):
        """
        Parses one line of scontrol job
        output and returns a dict built
        from that information.
        """
        log.debug("Getting job details from scontrol")
        job_dict = {}
        output = output.lower()
        for key, replacement in self.slurm_replacement_fields:
            output = output.replace(key,replacement)
        for field in output.split(' '):
            try:
                k, v = field.split('=')
            except ValueError:
                break
            if k.lower() == 'user':
                v = v.split('(')[0]
            job_dict[k.lower()] = v
        return job_dict

    def _set_remote_time(self):
        """
        Returns the time as observed by the SLURM controller.
        """
        log.debug("Setting remote time from cluster")
        try:
            remote_date = '\n'.join(self.master.ssh.execute('date'))
        except self.remote_exceptions, e:
            raise RemoteCommandError(
                "Unable to get the current system time from the cluster: " \
                + str(e))
        self._remote_time = \
            datetime.datetime.strptime(remote_date, "%a %b %d %H:%M:%S UTC %Y")

    def _get_remote_time_epoch(self):
        """
        Returns the remote epoch time.
        """
        log.debug("Getting remote time epoch")
        return time.mktime(self.remote_time.timetuple())

    def _get_job_submit_time_epoch(self, job):
        """
        Returns the time at which a job was submitted.
        """
        log.debug("Getting job submit time")
        try:
            return time.mktime(
                    datetime.datetime.strptime(
                        job.submit, self.slurm_time_format).timetuple())
        except ValueError:
            return "N/A"

    def _str_to_date(self, str):
        """
        Converts a string date from SLURM to a datetime object.
        """
        return datetime.datetime.strptime(str, self.slurm_time_format)

    def _nodes_needed_for_all_jobs(self):
        """
        Returns the number of nodes needed to complete
        all jobs in the queue.
        """
        return sum([int(job.nodes) for job in self.queued_jobs])

    def _set_est_ttc(self):
        """
        Sets the estimated time to completion for
        the given number of hosts

        Calculated as:
        W + D*N/n

        W = average job wait
        D = average job duration
        N = nodes needed for all jobs to begin
        n = nodes present
        """
        log.debug("Computing ettc")
        if len(self.nodes) == 0 or not \
           (self.has_pending_jobs or self.has_running_jobs):
            self._est_ttc = 0
        else:
            self._est_ttc = self.average_job_wait + \
                self.average_job_duration * \
                  self._nodes_needed_for_all_jobs() / float(len(self.nodes))


class SlurmLoadBalancerError(Exception):
    """ Base class exception handler """
    pass


class RemoteCommandError(SlurmLoadBalancerError):

    def __init__(self, msg):
        self.msg = \
            "There was an error executing command on the cluster: " + msg
        super(RemoteCommandError, self).__init__()

    def __str__(self):
        return repr(self.msg)


class SlurmControllerError(SlurmLoadBalancerError):

    def __init__(self, msg):
        self.msg = \
            "There was an error with the SLURM controller.  Make sure " \
            + "that the SLURM controller daemon (slurmctld) is still " \
            + "running on the master node.  You can debug the daemon " \
            + "on the master node by running: slurmctld -D " \
            + "Error: " + msg
        super(SlurmControllerError, self).__init__()

    def __str__(self):
        return repr(self.msg)
