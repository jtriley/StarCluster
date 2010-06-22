from starcluster.logger import log
from starcluster import cluster
from starcluster import config 

class LoadBalancer(object):
    def __init__(self):
        pass

    def run(self):
        pass

    if __name__ == "__main__":
        cfg = config()
        cl = cluster.get_cluster('mycluster',cfg)
        b = SGELoadBalancer()
        b.get_stats(cl)
        #balancer = LoadBalancer(cl)
        #balancer.run()
