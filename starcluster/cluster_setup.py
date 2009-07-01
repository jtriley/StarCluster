#!/usr/bin/env python

"""
cluster_setup.py
"""

import os
import logging

from starcluster.starclustercfg import *
from templates.sgeprofile import sgeprofile_template
from templates.sgeinstall import sgeinstall_template
from templates.sge_pe import sge_pe_template

log = logging.getLogger('starcluster')

def setup_cluster_user(nodes):
    log.info("Creating cluster user: %s" % CLUSTER_USER)
    for node in nodes:
        nconn = node['CONNECTION']
        nconn.execute('useradd -m -s /bin/bash %s' % CLUSTER_USER)

def setup_scratch(nodes):
    log.info("Configuring scratch space for user: %s" % CLUSTER_USER)
    for node in nodes:
        nconn = node['CONNECTION']
        nconn.execute('mkdir /mnt/%s' % CLUSTER_USER)
        nconn.execute('chown -R %(user)s:%(user)s /mnt/%(user)s' % {'user':CLUSTER_USER})
        nconn.execute('mkdir /scratch')
        nconn.execute('ln -s /mnt/%s /scratch' % CLUSTER_USER)

def setup_etc_hosts(nodes):
    log.info("Configuring /etc/hosts on each node")
    for node in nodes:
        conn = node['CONNECTION']
        host_file = conn.remote_file('/etc/hosts')
        print >> host_file, "# Do not remove the following line or programs that require network functionality will fail"
        print >> host_file, "127.0.0.1 localhost.localdomain localhost"
        for node in nodes:
            print >> host_file, "%(INTERNAL_IP)s %(INTERNAL_NAME)s %(INTERNAL_NAME_SHORT)s %(INTERNAL_ALIAS)s" % node 
        host_file.close()

def setup_passwordless_ssh(nodes):
    log.info("Configuring passwordless ssh for root")
    for node in nodes:
        conn = node['CONNECTION']
        conn.put(KEY_LOCATION,'/root/.ssh/id_rsa')
        conn.execute('chmod 400 /root/.ssh/id_rsa')

    master = nodes[0]
    mconn = master['CONNECTION']

    # make initial connections to all nodes to skip host key checking on first use
    # this basically populates /root/.ssh/known_hosts which is copied to CLUSTER_USER below
    for node in nodes:
        mconn.execute('ssh -o "StrictHostKeyChecking=no" %(INTERNAL_IP)s hostname' % node)
        mconn.execute('ssh -o "StrictHostKeyChecking=no" %(INTERNAL_NAME)s hostname' % node)
        mconn.execute('ssh -o "StrictHostKeyChecking=no" %(INTERNAL_NAME_SHORT)s hostname' % node)
        mconn.execute('ssh -o "StrictHostKeyChecking=no" %(INTERNAL_ALIAS)s hostname' % node)

    log.info("Configuring passwordless ssh for user: %s" % CLUSTER_USER)
    # only needed on master, nfs takes care of the rest
    mconn.execute('cp -r /root/.ssh /home/%s/' % CLUSTER_USER)
    mconn.execute('chown -R %(user)s:%(user)s /home/%(user)s/.ssh' % {'user':CLUSTER_USER})

def setup_ebs_volume(nodes):
    # setup /etc/fstab on master to use block device if specified
    if ATTACH_VOLUME is not None and VOLUME_PARTITION is not None:
        mconn = nodes[0]['CONNECTION']
        master_fstab = mconn.remote_file('/etc/fstab', mode='a')
        print >> master_fstab, "%s /home ext3 noauto,defaults 0 0 " % VOLUME_PARTITION
        master_fstab.close()
        mconn.execute('mount /home')

def setup_nfs(nodes):
    log.info("Configuring NFS...")

    master = nodes[0]
    mconn = master['CONNECTION']

    # copy fresh sge installation files to /opt/sge6 and make CLUSTER_USER the owner
    mconn.execute('cp -r /opt/sge6-fresh /opt/sge6')
    mconn.execute('chown -R %(user)s:%(user)s /opt/sge6' % {'user': CLUSTER_USER})

    # setup /etc/exports and start nfsd on master node
    nfs_export_settings = "(async,no_root_squash,no_subtree_check,rw)"
    etc_exports = mconn.remote_file('/etc/exports')
    for node in nodes:
        if node['NODE_ID'] != 0:
            etc_exports.write('/home/ ' + node['INTERNAL_NAME'] + nfs_export_settings + '\n')
            etc_exports.write('/opt/sge6 ' + node['INTERNAL_NAME'] + nfs_export_settings + '\n')
    etc_exports.close()
    
    mconn.execute('/etc/init.d/portmap start')
    mconn.execute('mount -t rpc_pipefs sunrpc /var/lib/nfs/rpc_pipefs/')
    mconn.execute('/etc/init.d/nfs start')
    mconn.execute('/usr/sbin/exportfs -r')
    mconn.execute('mount -t devpts none /dev/pts') # fix for xterm

    # setup /etc/fstab and mount /home and /opt/sge6 on each node
    for node in nodes:
        if node['NODE_ID'] != 0:
            nconn = node['CONNECTION']
            nconn.execute('/etc/init.d/portmap start')
            nconn.execute('mkdir /opt/sge6')
            nconn.execute('chown -R %(user)s:%(user)s /opt/sge6' % {'user':CLUSTER_USER})
            nconn.execute('echo "%s:/home /home nfs user,rw,exec 0 0" >> /etc/fstab' % master['INTERNAL_NAME'])
            nconn.execute('echo "%s:/opt/sge6 /opt/sge6 nfs user,rw,exec 0 0" >> /etc/fstab' % master['INTERNAL_NAME'])
            nconn.execute('mount /home')
            nconn.execute('mount /opt/sge6')
            nconn.execute('mount -t devpts none /dev/pts') # fix for xterm

def setup_sge(nodes):
    log.info("Installing Sun Grid Engine...")

    # generate /etc/profile.d/sge.sh for each node
    for node in nodes:
        conn = node['CONNECTION']
        sge_profile = conn.remote_file("/etc/profile.d/sge.sh")
        arch = conn.execute("/opt/sge6/util/arch")[0]

        print >> sge_profile, sgeprofile_template  % {'arch': arch}
        sge_profile.close()

    # setup sge auto install file
    master = nodes[0]
    mconn = master['CONNECTION']

    admin_list = ''
    for node in nodes:
        admin_list = admin_list + " " +node['INTERNAL_NAME']

    exec_list = admin_list
    submit_list = admin_list
    ec2_sge_conf = mconn.remote_file("/opt/sge6/ec2_sge.conf")

    # todo: add sge section to config values for some of the below
    print >> ec2_sge_conf, sgeinstall_template % (admin_list, exec_list, submit_list)
    ec2_sge_conf.close()

    # installs sge in /opt/sge6 and starts qmaster and schedd on master node
    mconn.execute('cd /opt/sge6 && TERM=rxvt ./inst_sge -m -x -auto ./ec2_sge.conf', silent=True)

    # set all.q shell to bash
    mconn.execute('source /etc/profile && qconf -mattr queue shell "/bin/bash" all.q')

    # create sge parallel environment
    # first iterate through each machine and count the number of processors
    num_processors = 0
    for node in nodes:
        conn = node['CONNECTION']
        num_procs = int(conn.execute('cat /proc/cpuinfo | grep processor | wc -l')[0])
        num_processors += num_procs

    parallel_environment = mconn.remote_file("/tmp/pe.txt")
    print >> parallel_environment, sge_pe_template % num_processors
    parallel_environment.close()
    mconn.execute("source /etc/profile && qconf -Ap %s" % parallel_environment.name)

    mconn.execute('source /etc/profile && qconf -mattr queue pe_list "orte" all.q')

    #todo cleanup /tmp/pe.txt 
    log.info("Done Configuring Sun Grid Engine")

def main(nodes):
    setup_ebs_volume(nodes)
    setup_cluster_user(nodes)
    setup_scratch(nodes)
    setup_etc_hosts(nodes)
    setup_nfs(nodes)
    setup_passwordless_ssh(nodes)
    setup_sge(nodes)
