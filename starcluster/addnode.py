#!/usr/bin/env python
from starcluster.logger import log

def add_to_sge(master, node):
    pass

def setup_etc_exports(cluster):
    pass

def setup_etc_hosts(cluster):
    """ Configure /etc/hosts on all StarCluster nodes"""
    log.info("Configuring /etc/hosts on each node")
    for node in cluster.nodes:
        conn = node.ssh
        host_file = conn.remote_file('/etc/hosts')
        print >> host_file, "# Do not remove the following line or programs that require network functionality will fail"
        print >> host_file, "127.0.0.1 localhost.localdomain localhost"
        for node in cluster.nodes:
            print >> host_file, node.get_hosts_entry()
        host_file.close()

def add_node(cluster, num_nodes):
    cluster.load_receipt()
    cluster_sg = cluster.cluster_group.name
    current_num_nodes = len([i for i in cluster.cluster_group.instances() if i.state in ['pending','running'])
    for id in range(current_num_nodes, current_num_nodes + num_nodes):
        alias = 'node%.3d' % id
        cluster.create_node(alias)
    cluster.cluster_size = current_num_nodes + num_nodes
    cluster._nodes = None
    s = Spinner()
    log.log(INFO_NO_NEWLINE, "Waiting for nodes to come up...")
    while not cluster.is_cluster_up():
        time.sleep(30)
    s.stop()
    setup_etc_hosts(cluster)
