#!/usr/bin/env python
"""
StarCluster SunGrinEngine stats parsing module
"""
import types
import time
import datetime
import logging
import xml.dom.minidom
from xml.dom.minidom import Node
from starcluster import balancers
from starcluster.balancers import LoadBalancer 
from starcluster import utils
from starcluster import config
from starcluster import cluster
from starcluster.logger import log, INFO_NO_NEWLINE
from starcluster.utils import print_timing
from starcluster.removenode import remove_node
from starcluster.addnode import add_nodes

class SGEStats(object):
    hosts = []
    jobs = []
    jobstats = []
    _default_fields = \
        ["JB_job_number","state","JB_submission_time","queue_name","slots"]

    def parse_qhost(self,string):
        """
        this function parses qhost -xml output and makes a neat array
        takes in a string, so we can pipe in output from ssh.exec('qhost -xml')
        """
        self.hosts = [] #clear the old hosts
        doc = xml.dom.minidom.parseString(string)
        for h in doc.getElementsByTagName("host"):
            name = h.getAttribute("name")
            hash = {"name" : name }
            for stat in h.getElementsByTagName("hostvalue"):
                for hvalue in stat.childNodes:
                    attr = stat.attributes['name'].value
                    val = ""
                    if hvalue.nodeType == Node.TEXT_NODE:
                        val = hvalue.data
                    hash[attr] = val
            if hash['name'] != u'global':
                self.hosts.append(hash)
        return self.hosts

    def parse_qstat(self,string, fields=None):
        """
        This method parses qstat -xml oputput and makes a neat array 
        """
        if fields == None:
            fields = self._default_fields
        self.jobs = [] #clear the old jobs
        doc = xml.dom.minidom.parseString(string)
        for job in doc.getElementsByTagName("job_list"):
            jstate = job.getAttribute("state")
            hash = {"job_state" : jstate }
            for tag in fields:
                es = job.getElementsByTagName(tag)
                for node in es:
                    for node2 in node.childNodes:
                        if node2.nodeType == Node.TEXT_NODE:
                            hash[tag] = node2.data 
            #grab the submit time on all jobs, the last job's val stays
            self.jobs.append(hash)
        return self.jobs

    def parse_qacct(self,string,dtnow):
        """
        This method parses qacct -j output and makes a neat array and
        calculates some statistics.
        Takes the string to parse, and a datetime object of the remote
        host's current time.
        """
        self.jobstats = []
        qd = None
        start = None
        end = None

        lines = string.split('\n')
        for l in lines:
            l = l.strip()
            if l.find('qsub_time') != -1:
                    qd = utils.qacct_to_datetime_tuple(l[13:len(l)])
            
            if l.find('start_time') != -1:
                    if l.find('-/-') >0:
                        start = dtnow
                    else:
                        start = utils.qacct_to_datetime_tuple(l[13:len(l)])

            if l.find('end_time') != -1:
                    if l.find('-/-') > 0:
                        end = dtnow
                    else:
                        end = utils.qacct_to_datetime_tuple(l[13:len(l)])

            if l.find('==========') != -1:
                if qd != None:
                    hash = {'queued' : qd, 'start' : start, 'end' : end}
                    self.jobstats.append(hash)
                qd = None
                start = None
                end = None
        return self.jobstats


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
            slots = slots + int(h['num_proc'])
        return slots

    def slots_per_host(self):
        """
        returns the number of slots per host.
        If for some reason the cluster is inconsistent, this will return -1
        for example, if you have m1.large and m1.small in the same cluster
        """
        total = self.count_total_slots()
        single = int(self.hosts[0][u'num_proc'])
        if (total != (single * len(self.hosts))):
            log.error("ERROR: Number of slots is not consistent across cluster")
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
        nodename = node.private_dns_name
        for j in self.jobs:
            if 'queue_name' in j:
                qn = j['queue_name']
                if qn.find(nodename) > 0:
                    log.debug("Node %s is working." % node.id)
                    return True
        log.debug("Node %s is IDLE." % node.id)
        return False

    def num_slots_for_job(self,job_id):
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
            delta = job['start'] - job['queued']
            total_seconds = total_seconds + delta.seconds
            count = count + 1
        if count == 0:
            return 0
        else:
            return total_seconds / count

    def on_first_job(self):
        """
        returns true if the cluster is processing the first job, False otherwise
        """
        if len(self.jobs) > 0 and self.jobs[0]['JB_job_number'] != u'1':
            print "ON THE FIRST JOB"
            return True
        return False

    def get_loads(self):
        """
        returns an array containing the loads on each host in cluster
        """
        loads = []
        for h in self.hosts:
            loads.append(h['load_avg'])
        return loads

class SGELoadBalancer(LoadBalancer):
    """
    This class is able to query each SGE host and return with load & queue statistics
    """
    #       *** All times are in SECONDS unless otherwise specified ***

    #The polling interval in seconds. recommended: 60-300. any more frequent is
    #very wasteful. the polling loop with visualizer takes about 15 seconds.
    polling_interval = 60

    #VERY IMPORTANT: Set this to the max nodes you're willing to have in your
    #cluster. Try setting this to the default cluster size you'd ordinarily use.
    max_nodes = 5

    #IMPORTANT: Set this to the longest time a job can wait before another host
    #is added to the cluster to help. Recommended: 300-900 seconds (5-15 mins).
    #Do not use a value less than 300 seconds because that is how long an
    #instance will take to start up.
    longest_allowed_queue_time = 900

    #Keep this at 1 - your master, for now.
    min_nodes = 1

    #This would allow the master to be killed when the queue empties. UNTESTED.
    allow_master_kill = False
    
    #How many nodes to add per iteration. Setting it > 1 opens up possibility
    #of spending too much $$
    add_nodes_per_iteration = 1
    
    #Kill an instance after it has been up for X minutes. Do not kill earlier,
    #Since you've already paid for that hour. In Minutes.
    kill_after = 45
       
    #After adding a node, how long to wait for the instance to start new jobs
    stabilization_time = 180

    #Visualizer off by default. Start it with "starcluster loadbalance -p tag"
    _visualizer_on = False

    #How many hours qacct should look back to gather past job data. lower
    #values minimize data transfer
    lookback_window = 3

    #not for modification
    _keep_polling = True
    __last_cluster_mod_time = datetime.datetime.utcnow()


    def __init__(self, cluster_tag, config,interval,plot):
        """
        this is the constructor for SGELoadBalancer.
        """
        self._cluster_tag = cluster_tag
        self._cfg = config
        self._cluster = cluster.get_cluster(cluster_tag, self._cfg)
        if self.longest_allowed_queue_time < 300:
            log.warn("Longest Allowed Queue Time should be > 300 seconds.")
            log.warn("It takes ~5 minutes to launch a new EC2 node.")
        if interval != None:
            self.polling_interval = interval
            log.debug("SGELoadBalancer: polling interval set to %d seconds." 
                      % polling_interval)
        if plot == True:
            self._visualizer_on = True
            log.debug("SGELoadBalancer: visualizer enabled.")

    def get_qatime(self):
        """
        this function takes the lookback window and creates a string
        representation of the past few hours, to feed to qacct to
        limit the data set qacct returns.
        """
        if self.lookback_window > 24 or self.lookback_window < 1:
            log.warn("Lookback window %d out of range (1..24). Not recommended." % \
                    self.lookback_window)
        now = utils.get_remote_time(self._cluster)
        now = now.replace(hour=now.hour - self.lookback_window)
        str = now.strftime("%Y%m%d%H%M")
        return str


    #@print_timing
    def get_stats(self):
        """
        this function will ssh to the SGE master and get load & queue stats.
        it will feed these stats to SGEStats, which parses the XML.
        it will return two arrays: one of hosts, each host has a hash with its 
        host information inside. The job array contains a hash for every job,
        containing statistics about the job name, priority, etc
        """
        log.debug("starting get_stats")
        master = self._cluster.master_node
        self.stat = SGEStats()

        qatime = self.get_qatime()

        qhostXml = ""
        qstatXml = ""
        qacct = ""
        qacct_cmd = 'source /etc/profile && qacct -j -b ' + qatime
        try:
            qhostXml = '\n'.join(master.ssh.execute('source /etc/profile && qhost -xml', \
                                                    log_output=False))
            qstatXml = '\n'.join(master.ssh.execute('source /etc/profile && qstat -xml', \
                                                    log_output=False))
            qacct = '\n'.join(master.ssh.execute(qacct_cmd,log_output=False))
            now = utils.get_remote_time(self._cluster)
        except Exception, e:
            log.error("Error occured getting SGE stats via ssh. Cluster terminated?")
            log.error(e)
            return -1

        log.debug("sizes: qhost: %d, qstat: %d, qacct: %d." % \
                  (len(qhostXml),len(qstatXml),len(qacct)))

        self.stat.parse_qhost(qhostXml)
        self.stat.parse_qstat(qstatXml)
        self.stat.parse_qacct(qacct,now)
    
    #@print_timing
    def _call_visualizer(self):
        if not self._visualizer_on:
            return
        try:
            from starcluster.balancers.sge import visualizer
        except ImportError,e:
                log.error("Error importing matplotlib and numpy:")
                log.error(str(e)) 
                log.error("check that matplotlib and numpy are installed and:")
                log.error("   $ python -c 'import matplotlib'")
                log.error("   $ python -c 'import numpy'")
                log.error("completes without error")
                log.error("Visualizer has been disabled.")
                #turn the visualizer off, but keep going.
                self._visualizer_on = False
                return

        visualizer = visualizer.SGEVisualizer()
        visualizer.record(self.stat)
        visualizer.read()
        visualizer.graph_all()


    def run(self):
        """
        this is a rough looping function. it will loop indefinitely, using 
        SGELoadBalancer.get_stats()
        to get the clusters status. It will look at the job queue and try to 
        decide whether to add or remove a node. It should later look at job
        durations. Doesn't yet.
        """
        while(self._keep_polling):
            if not self.are_nodes_up(self._cluster):
                log.info("Entire cluster is not up,nodes added/removed. No Action.")
                time.sleep(self.polling_interval)
                continue

            if self.get_stats() == -1:
                log.error("Failed to get stats. LoadBalancer is terminating.")
                return

            log.info("Oldest job is from %s. # queued jobs = %d. # hosts = %d."  
                     % (self.stat.oldest_queued_job_age(), 
                     len(self.stat.get_queued_jobs()), len(self.stat.hosts)))

            log.info("Avg job duration = %d sec, Avg wait time = %d sec." %
                     (self.stat.avg_job_duration(), self.stat.avg_wait_time()))

            #evaluate if nodes need to be added
            self._eval_add_node()

            #evaluate if nodes need to be removed
            self._eval_remove_node()

            #call the visualizer
            self._call_visualizer()

            #sleep for the specified number of seconds
            log.info("Sleeping, looping again in %d seconds.\n" 
                     % self.polling_interval)
            time.sleep(self.polling_interval)

    def _eval_add_node(self):
        """
        This function uses the metrics available to it to decide whether to
        add a new node to the cluster or not. It isn't able to add a node yet.
        TODO: See if the recent jobs have taken more than 5 minutes (how
        long it takes to start an instance)
        """
        need_to_add = 0
        if len(self.stat.hosts) >= self.max_nodes:
            log.info( "Won't add another host, currently at max (%d)." % \
                   self.max_nodes)
            return 0
        qlen = len(self.stat.get_queued_jobs())
        sph = self.stat.slots_per_host()
        ts = self.stat.count_total_slots()

        #calculate job duration
        avg_duration = self.stat.avg_job_duration()
        #calculate estimated time to completion
        ettc = avg_duration * qlen

        if qlen > ts:
            now = datetime.datetime.utcnow()
            if (now - self.__last_cluster_mod_time).seconds < self.stabilization_time:
               log.info("Cluster change was made less than %d seconds ago (%s)."
                        % (self.stabilization_time, self.__last_cluster_mod_time))
               log.info("Not changing cluster size until cluster stabilizes." )

               return 0

            #there are more jobs queued than will be consumed with one
            #cycle of job processing from all nodes
            oldest_job_dt = self.stat.oldest_queued_job_age()
            now = utils.get_remote_time(self._cluster)
            age_delta = now - oldest_job_dt
            if age_delta.seconds > self.longest_allowed_queue_time:
                log.info("A job has been waiting for %d sec, longer than max %d." 
                         % (age_delta.seconds, self.longest_allowed_queue_time))
                need_to_add = qlen / sph
                
                if ettc < 300 and not self.stat.on_first_job():
                    log.warn("There is a possibility that the job queue is" + \
                             " shorter than 5 minutes in duration.")
        
        if need_to_add > 0:
            need_to_add = min(self.add_nodes_per_iteration, need_to_add)
            log.info("*** ADDING %d NODES." % need_to_add)
            try:
                add_nodes(self._cluster, need_to_add)
            except Exception, e:
                   log.error("Failed to add new host.")
                   log.error("Exception Type: %s, Message: %s" % \
                        (type(e),e))
                   return -1

            self.__last_cluster_mod_time = datetime.datetime.utcnow()
            log.info("Done adding nodes.")
        return need_to_add

    def _node_alive(self, node_id):
        """
        this function iterates through the cluster's list of active nodes,
        and makes sure that the specified node is there and 'running'
        """
        for n in self._cluster.nodes:
            if n.id == node_id and n.state == 'running':
                return True
        return False

    def _eval_remove_node(self):
        """
        This function uses the metrics available to it to decide whether to
        remove a new new from the cluster. It isn't able to actually remove 
        a node yet.
        """
        qlen = len(self.stat.get_queued_jobs())
        if qlen == 0:
           now = datetime.datetime.utcnow()
           if (now - self.__last_cluster_mod_time).seconds < self.stabilization_time:
               log.info("Cluster change was made less than %d seconds ago (%s)."
                        % (self.stabilization_time, self.__last_cluster_mod_time))
               log.info("Not changing cluster size until cluster stabilizes." )
               return 0

           #if at 0, remove all nodes but master
           if len(self.stat.hosts) > self.min_nodes:
               log.info("Checking to remove a node...")
               to_kill = self._find_node_for_removal()
               if len(to_kill) == 0:
                   log.info("No nodes can be killed at this time.")
               #kill the nodes returned
               for n in to_kill:
                   if self._node_alive(n.id):
                       log.info("***KILLING NODE: %s (%s)." % (n.id,n.dns_name))
                       try:
                           remove_node(n,self._cluster) 
                       except Exception, e:
                           log.error("Failed to terminate the host.")
                           log.error("Exception Type: %s, Message: %s" % \
                                (type(e),e))
                           return -1
                       #successfully removed node
                       self.__last_cluster_mod_time = datetime.datetime.utcnow()
                   else:
                        log.error("Trying to kill a dead node! id = %s." % n.id)
           else:
               log.info("Can't remove a node, already at min (%d)." 
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
            if not self.allow_master_kill and \
                    node.id == self._cluster.master_node.id:
                log.debug("not removing master node")
                continue

            is_working = self.stat.is_node_working(node)
            mins_up = self._minutes_uptime(node) % 60
            if not is_working:
                log.info("Idle Node %s (%s) has been up for %d minutes past the hour."
                      % (node.id,node.alias,mins_up))

            if self.polling_interval > 300:
                self.kill_after = max(45,60 - (2*self.polling_interval/60))

            if not is_working and mins_up > self.kill_after:
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
        now = utils.get_remote_time(self._cluster)
        timedelta = now - dt
        return timedelta.seconds / 60

    def are_nodes_up(self,cl):
        """
        Check whether the nodes in the cluster are all up,
        that ssh (port 22) is up on all nodes, and that each node
        has an internal ip address associated with it. Pass in a cluster.
        """
        nodes = cl.running_nodes
        for node in nodes:
            if not node.is_up():
                return False
        return True

    if __name__ == "__main__":
        #TODO: replace this with something else or delete
        cfg = config.StarClusterConfig()
        cl = cluster.get_cluster('mycluster',cfg)
        balancer = LoadBalancer(cl)
        balancer.run()
