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
    print ">>> SETTING UP NFS"
    if nodes is None:
        return

    master = socket.getfqdn()

    os.system('rm -rf /opt/sge6')
    os.system('cp -r /opt/sge6-fresh /opt/sge6')

    print ">>> changing ownership of /opt/sge6 to %s" % CLUSTER_USER
    os.system('chown -R %(user)s:%(user)s /opt/sge6' % {'user': CLUSTER_USER})

    # setup /etc/exports and start nfsd on master node
    nfs_export_settings = "(async,no_root_squash,no_subtree_check,rw)"
    etc_exports = open('/etc/exports','w')

    for node in nodes:
        etc_exports.write('/home/ ' + node + nfs_export_settings + '\n')
        etc_exports.write('/opt/sge6 ' + node + nfs_export_settings + '\n')
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
        ssh(node, cmd='mount /home', user=CLUSTER_USER)
        ssh(node, cmd='mount /opt/sge6', user=CLUSTER_USER)

        # fix xterm as well
        ssh(node, cmd='mount -t devpts none /dev/pts')

def setup_nodes(nodes = None):
    print ">>> SETTING UP NODES"
    if nodes is None:
        return

    #send a copy of the hosts file to each of the compute nodes...
    for host in nodes:
        # copy over the ssh folder and host config to all machines in cluster (both /root and /home/USER)
        scp(host, src='/home/%s/.ssh' % CLUSTER_USER, dest="/home/%s/" % CLUSTER_USER, recursive=True)
        ssh(host, cmd="chown -R %(user)s:%(user)s /home/%(user)s/.ssh" % {'user':CLUSTER_USER})
        scp(host, src='/etc/mpd.hosts', dest="/etc/")
        scp(host, src='/etc/mpd.hosts', dest="/usr/local/etc/openmpi-default-hostfile")

        # copy /etc/hosts to node at /etc and /home/%s
        scp(host, src='/etc/hosts', dest='/etc/')

def setup_sge(nodes = None):
    print ">>> SETTING UP SGE"
    if nodes is None:
        return

    master = socket.getfqdn()
    slaves = nodes

    admin_list = master
    for slave in slaves:
        admin_list = admin_list + " " +slave

    exec_list = admin_list
    submit_list = admin_list
    ec2_sge_conf = open("/opt/sge6/ec2_sge.conf","w")

    print >> ec2_sge_conf, """
SGE_ROOT="/opt/sge6"
SGE_QMASTER_PORT="63231"
SGE_EXECD_PORT="63232"
CELL_NAME="default"
ADMIN_USER=""
QMASTER_SPOOL_DIR="/opt/sge6/default/spool/qmaster"
EXECD_SPOOL_DIR="/opt/sge6/default/spool"
GID_RANGE="20000-20100"
SPOOLING_METHOD="classic"
DB_SPOOLING_SERVER="none"
DB_SPOOLING_DIR="/opt/sge6/default/spooldb"
PAR_EXECD_INST_COUNT="20"
ADMIN_HOST_LIST="%s"
SUBMIT_HOST_LIST="%s"
EXEC_HOST_LIST="%s"
EXECD_SPOOL_DIR_LOCAL="/opt/sge6/default/spool/exec_spool_local"
HOSTNAME_RESOLVING="true"
SHELL_NAME="ssh"
COPY_COMMAND="scp"
DEFAULT_DOMAIN="none"
ADMIN_MAIL="star@mit.edu"
ADD_TO_RC="false"
SET_FILE_PERMS="true"
RESCHEDULE_JOBS="wait"
SCHEDD_CONF="1"
SHADOW_HOST=""
EXEC_HOST_LIST_RM=""
REMOVE_RC="false"
WINDOWS_SUPPORT="false"
WIN_ADMIN_NAME="Administrator"
WIN_DOMAIN_ACCESS="false"
CSP_RECREATE="false"
CSP_COPY_CERTS="false"
CSP_COUNTRY_CODE="US"
CSP_STATE="Massachusetts"
CSP_LOCATION="NE48"
CSP_ORGA="Massachusetts Institute of Technology - MIT"
CSP_ORGA_UNIT="Office of Educational Innovation and Technology"
CSP_MAIL_ADDRESS="star@mit.edu"
    """ % (admin_list, exec_list, submit_list)
    ec2_sge_conf.close()
    print "SGE_CONF(): changing ownership of /opt/sge6 to %s" % CLUSTER_USER
    os.system('chown -R %(user)s:%(user)s /opt/sge6/' % {'user':CLUSTER_USER})

    # installs sge in /opt/sge6 and starts qmaster and schedd on master node
    cwd = os.getcwd()
    os.chdir('/opt/sge6/')
    os.system('TERM=rxvt ./inst_sge -m -x -auto ec2_sge.conf')
    os.chdir(cwd)

def main():
    print 'RUNNING AS:'
    os.system('whoami')
    # run master node commands locally, below we do this on each node
    os.system('cp /etc/mpd.hosts /home/%s/' % CLUSTER_USER)
    os.system('cp /etc/mpd.hosts /usr/local/etc/openmpi-default-hostfile')

    os.system("cp /etc/hosts /home/%s/" % CLUSTER_USER)
    os.system("chown -R %(user)s:%(user)s /home/%(user)s/" % {'user':CLUSTER_USER})

    # Configure /etc/hosts file...
    # read the internal domain names listed in mpd.hosts to construct this file
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
    os.system("chown -R %(user)s:%(user)s /home/%(user)s" % {'user':CLUSTER_USER}) 
    
    setup_nodes(workernames)
    setup_nfs(workernames)
    setup_sge(workernames)
    os.system('rm /home/*.py*')

if __name__ == '__main__':
    main()
