#!/usr/bin/env python
"""
StarCluster SunGrinEngine stats parsing module
"""
import types
import logging
import xml.dom.minidom
from xml.dom.minidom import Node
from starcluster import balancers
from starcluster.balancers import LoadBalancer 


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

class SGELoadBalancer(LoadBalancer):
    """
    This class is able to query each SGE host and return with load & queue statistics
    """
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
        stat = SGEStats()
        qhostXml = '\n'.join(master.ssh.execute('source /etc/profile && qhost -xml'))
        qstatXml = '\n'.join(master.ssh.execute('source /etc/profile && qstat -xml'))

        hostHash = stat.parse_qhost(qhostXml)
        statHash = stat.parse_qstat(qstatXml)

        print hostHash
        print statHash


    if __name__ == "__main__":
        print LoadBalancer()
        cfg = config.StarClusterConfig()
        cl = cluster.get_cluster('mycluster',cfg)
        balancer = LoadBalancer(cl)
        balancer.run()
