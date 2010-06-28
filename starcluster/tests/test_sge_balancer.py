from starcluster.logger import log
from starcluster.tests import StarClusterTest

class TestSGELoadBalancer(StarClusterTest):

    def test_qhost_parser(self):
        assert 1==1
    def test_qstat_parser(self):
        assert 1==1


#TEST FUNCTIONS
#xmlFile = "/home/rajat/files/qhost.xml"
#f = open(xmlFile, 'r')
#xText = XmlParser()
#print xText.parseQHost(f.read())
#f.close()
#print "Number of hosts: "  
#print xText.hostCount()

#xmlFile = "/home/rajat/files/qstat.xml"
#f = open(xmlFile,'r')
#print xText.parseQStat(f.read())
#f.close()
