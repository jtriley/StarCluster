#!/usr/bin/env python

"""
create_hosts.py
"""

import sys
import os
import socket
from EC2config import *
from ssh import ssh,scp

def setup_nfs(nodes = None):
    if nodes is None:
        return

    master = socket.getfqdn()

    # setup /etc/exports and fire up nfsd on master node
    
    nfs_export_settings = "(async,no_root_squash,no_subtree_check,rw)"
    etc_exports = open('/etc/exports','w')

    for node in nodes:
        etc_exports.write('/home/ ' + node + nfs_export_settings + '\n')
    etc_exports.close()
    
    os.system('/etc/init.d/portmap start')
    os.system('mount -t rpc_pipefs sunrpc /var/lib/nfs/rpc_pipefs/')
    os.system('/etc/init.d/nfs start')
    os.system('/usr/sbin/exportfs -r')
    os.system('mount -t devpts none /dev/pts')

    # setup /etc/fstab and mount /opt/sge6 on each node

    for node in nodes:
        ssh(node, cmd='/etc/init.d/portmap start')
        ssh(node, cmd='echo "%s:/home /home nfs user,rw,exec 0 0" >> /etc/fstab' % master)
        ssh(node, cmd='mount /home')
        # fix xterm as well
        ssh(node, cmd='mount -t devpts none /dev/pts')

def setup_nodes(nodes = None):
    if nodes is None:
        return

    #send a copy of the hosts file to each of the compute nodes...
    for host in nodes:
        # copy over the ssh folder and host config to all machines in cluster (both /root and /home/USER)
        scp(host, src='/home/%s/.ssh' % CLUSTER_USER, dest="/home/%s/" % CLUSTER_USER, recursive=True)
        ssh(host, cmd="chown -R %s:%s /home/%s/.ssh" % CLUSTER_USER)
        scp(host, src='/etc/mpd.hosts', dest="/etc/")
        scp(host, src='/etc/mpd.hosts', dest="/usr/local/etc/openmpi-default-hostfile")

        # copy /etc/hosts to node at /etc and /home/%s
        scp(host, src='/etc/hosts', dest='/etc/')


def main():
    # run master node commands locally, below we do this on each node
    os.system('cp /etc/mpd.hosts /home/%s/' % CLUSTER_USER)
    os.system('cp /etc/mpd.hosts /usr/local/etc/openmpi-default-hostfile')

    os.system("cp /etc/hosts /home/%s" % CLUSTER_USER)
    os.system("chown -R %s:%s /home/%s/" % CLUSTER_USER)

    # Configure /etc/hosts file...
    #read the internal domain names listed in mpd.hosts to construct this file
    name_file = open("/etc/mpd.hosts", 'r')
    h_output=open("/etc/hosts",'w') 
    
    workernames=[]
    i=0
    
    for line in name_file.readlines():
        host = line.strip()
        #host example: domU-12-31-35-00-1C-A4.z-2.compute-1.internal
        ip = socket.gethostbyname(host)     
        shortname = host.split('.')[0]
        print host

        if i == 0:
            print >> h_output, "# Do not remove the following line or programs that require network functionality will fail"
            print >> h_output, "127.0.0.1 localhost.localdomain localhost"  
            print >> h_output, "%s %s %s master" % (ip, host, shortname)    
            print >> h_output, ""
            print >> h_output, "# Compute Nodes"    
        else:
            workernames.append(host)
            print >> h_output, "%s %s %s %s" % (ip, host, shortname, 'node%.3d' % i)   
        i+=1    
    
    name_file.close()
    h_output.close()

    #copy hosts file to %s directory
    os.system('cp /etc/hosts /home/%s/' % CLUSTER_USER)
    os.system("chown -R %s:%s /home/%s" % CLUSTER_USER) 
    
    setup_nodes(workernames)
    setup_nfs(workernames)

if __name__ == '__main__':
    main()
