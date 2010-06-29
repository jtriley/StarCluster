#!/usr/bin/env python
"""
StarCluster SunGrinEngine stats parsing module
"""
import types
import time
import logging
import xml.dom.minidom
from xml.dom.minidom import Node
from starcluster import balancers
from starcluster.balancers import LoadBalancer 
from starcluster import utils


class SGEStats(object):
    hosts = []
    jobs = []
    _default_fields = ["JB_job_number","state","JB_submission_time","queue_name"]

    #takes in a string, so we can pipe in output from ssh.exec('qhost -xml')
    def parse_qhost(self,string):
        """
        this function parses qhost -xml output and makes a neat array
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
            self.jobs.append(hash)
        return self.jobs

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
        returns a cound of the hosts in the cluster
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
            print "ERROR: Number of slots is not consistent across cluster"
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
                #print "Unicode = %s, dt = %s" % (st, dt)
                return dt
        #todo: throw a "no queued jobs" exception


class SGELoadBalancer(LoadBalancer):
    """
    This class is able to query each SGE host and return with load & queue statistics
    """
    stat = ""
    polling_interval = 30
    max_nodes = 20
    min_nodes = 1

    def __init__(self):
        pass

    def run(self):
        pass

    def get_stats(self, cl):
        """
        this function will ssh to the SGE master and get load & queue stats.
        it will feed these stats to SGEStats, which parses the XML.
        it will return two arrays: one of hosts, each host has a hash with its 
        host information inside. The job array contains a hash for every job,
        containing statistics about the job name, priority, etc
        """
        master = cl.master_node
        self.stat = SGEStats()
        qhostXml = '\n'.join(master.ssh.execute('source /etc/profile && qhost -xml'))
        qstatXml = '\n'.join(master.ssh.execute('source /etc/profile && qstat -xml'))

        hostHash = self.stat.parse_qhost(qhostXml)
        statHash = self.stat.parse_qstat(qstatXml)

        #print hostHash
        #print statHash

    def polling_loop(self,cl):
        
        while(1>0):
            self.get_stats(cl)
            print "Oldest job is from %s. # of queued jobs is %d. hosts=%d."  % \
            (self.stat.oldest_queued_job_age(), 
             len(self.stat.get_queued_jobs()), len(self.stat.hosts))

            #evaluate if nodes need to be added
            self._eval_add_node()

            #evaluate if nodes need to be removed
            self._eval_remove_node()

            #sleep for the specified number of seconds
            time.sleep(self.polling_interval)

    def _eval_add_node(self):
        if(len(self.stat.hosts) >= self.max_nodes):
            print "Can't add another host, already at max (%d)." % \
                   self.max_nodes
            return 0
        qlen = len(self.stat.get_queued_jobs())
        sph = self.stat.slots_per_host()

        if(qlen > sph):
            print "ADDING A NODE!"
            fakehost={"hostname":"fake"}
            self.stat.hosts.append(fakehost)

    def _eval_remove_node(self):
        qlen = len(self.stat.get_queued_jobs())
        if(qlen == 0):
           #if at 0, remove all nodes but master
           while(len(self.stat.hosts) > self.min_nodes):
               print "REMOVING A NODE!"
               self.stat.hosts.pop()
           else:
               print "Can't remove a node, already at min (%d)." % self.min_nodes


    if __name__ == "__main__":
        print LoadBalancer()
        cfg = config.StarClusterConfig()
        cl = cluster.get_cluster('mycluster',cfg)
        balancer = LoadBalancer(cl)
        balancer.run()
