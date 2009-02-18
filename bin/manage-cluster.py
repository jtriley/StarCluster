#!/usr/bin/env python

from optparse import OptionParser
from molsim.ec2utils import start_cluster, stop_cluster, ssh_to_master, ssh_to_node, list_instances

def main():
    usage = "usage: %prog [options] "
    parser = OptionParser(usage)

    parser.add_option("-s","--start-cluster", dest="start_cluster", action="store_true", default=False, help="start an amazon ec2 cluster")
    parser.add_option("-t","--terminate-cluster", dest="terminate_cluster", action="store_true", default=False, help="shutdown ec2 cluster")
    parser.add_option("-x","--no-create", dest="no_create", action="store_true", default=False, help="do not launch new ec2 instances when starting cluster (requires -s option, mostly for debug)")
    parser.add_option("-m","--login-master", dest="login_master", action="store_true", default=False, help="ssh to ec2 cluster master node (equivalent to -n 0")
    parser.add_option("-l","--list-nodes", dest="list_nodes", action="store_true", default=False, help="list all ec2 cluster nodes")
    parser.add_option("-n","--login-node", dest="login_node",  default=None, help="node number to connect to. (from output of -l option)")

    (options,args) = parser.parse_args() 

    if options.start_cluster:
        if options.no_create:
            start_cluster(create=False)
        else:
            start_cluster()
        if options.login_master:
            ssh_to_master()
    elif options.terminate_cluster:
        stop_cluster()
    elif options.login_master:
        ssh_to_master()
    elif options.list_nodes:
        list_instances()
    elif options.login_node:
        ssh_to_node(options.login_node)
    else:
        parser.print_help()
    
if __name__ == "__main__":
    main()
