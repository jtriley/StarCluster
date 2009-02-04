#!/usr/bin/env python

from optparse import OptionParser
from EC2config import *
from ec2utils import start_cluster, stop_cluster, ssh_to_master, list_instances

def main():
    usage = "usage: %prog [options] "
    parser = OptionParser(usage)

    parser.add_option("-s","--start-cluster", dest="start_cluster", action="store_true", default=False, help="start an amazon ec2 cluster")
    parser.add_option("-t","--terminate-cluster", dest="terminate_cluster", action="store_true", default=False, help="shutdown ec2 cluster")
    parser.add_option("-m","--login-master", dest="login_master", action="store_true", default=False, help="ssh to ec2 cluster master node")
    parser.add_option("-l","--list-nodes", dest="list_nodes", action="store_true", default=False, help="list all ec2 cluster nodes")

    (options,args) = parser.parse_args() 

    if options.start_cluster:
        start_cluster()
        if options.login_master:
            ssh_to_master()
    elif options.terminate_cluster:
        stop_cluster()
    elif options.login_master:
        ssh_to_master()
    elif options.list_nodes:
        list_instances()
    
if __name__ == "__main__":
    main()
