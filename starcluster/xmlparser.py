#!/usr/bin/env python
"""
StarCluster XML Parsing module
"""
import types
import logging
import xml.dom.minidom
from xml.dom.minidom import Node


class XmlParser(object):
    hosts = []
    jobs = []
    interested = ["JB_job_number","state","JB_submission_time","queue_name"]

    def __init__ (self):
	    pass

    def hostCount(self):
	    return len(self.hosts)

    #takes in a string, so we can pipe in output from ssh.exec('qhost -xml')
    def parseQHost(self,string):
	self.hosts = [] #clear the old hosts
    	doc = xml.dom.minidom.parseString(string)
	for h in doc.getElementsByTagName("host"):
		name = h.getAttribute("name")
		hash = {"name" : name }
		for stat in h.getElementsByTagName("hostvalue"):
			for node3 in stat.childNodes:
				attr = stat.attributes['name'].value
				val = ""
				if node3.nodeType == Node.TEXT_NODE:
					val = node3.data
				hash[attr] = val
        self.hosts.append(hash)
	return self.hosts

    def parseQStat(self,string):
	self.jobs = [] #clear the old jobs
	doc = xml.dom.minidom.parseString(string)
        for job in doc.getElementsByTagName("job_list"):
	    jstate = job.getAttribute("state")
	    hash = {"job_state" : jstate }
	    for tag in self.interested:
		    es = job.getElementsByTagName(tag)
		    for node in es:
			   for node2 in node.childNodes:
				   if node2.nodeType == Node.TEXT_NODE:
					  hash[tag] = node2.data 
	    self.jobs.append(hash)
	return self.jobs



#TEST FUNCTIONS
xmlFile = "/home/rajat/files/qhost.xml"
f = open(xmlFile, 'r')
xText = XmlParser()
print xText.parseQHost(f.read())
f.close()
print "Number of hosts: "  
print xText.hostCount()

xmlFile = "/home/rajat/files/qstat.xml"
f = open(xmlFile,'r')
print xText.parseQStat(f.read())
f.close()

