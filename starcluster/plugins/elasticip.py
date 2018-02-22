# Added by Daniel Treiman
# From Charles Cadieu http://star.mit.edu/cluster/mlarchives/1376.html


from starcluster import clustersetup
from starcluster.logger import log 


class ElasticIPSetup(clustersetup.ClusterSetup):
    def __init__(self, elastic_ip=None):
        super(ElasticIPSetup, self).__init__()
        self.elastic_ip = elastic_ip 
        log.debug('elastic_ip = %s' % elastic_ip) 

    def run(self, nodes, master, user, user_shell, volumes): 
        master.ec2.conn.associate_address(master.instance.id, self.elastic_ip) 
