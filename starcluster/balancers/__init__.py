#!/usr/bin/env python

from starcluster.balancers import sge


class LoadBalancer(object):
    def __init__(self):
        pass

    def run(self):
        pass

if __name__ == "__main__":
    from starcluster import config
    from starcluster import cluster
    cfg = config.StarClusterConfig()
    ec2 = cfg.get_easy_ec2()
    cm = cluster.ClusterManager(cfg, ec2)
    cl = cm.get_cluster('mycluster')
    b = sge.SGELoadBalancer()
    b.get_stats(cl)
    #balancer = LoadBalancer(cl)
    #balancer.run()
