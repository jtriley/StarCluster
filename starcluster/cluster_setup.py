#!/usr/bin/env python

"""
cluster_setup.py
"""

import os
import logging
#import tempfile

from starcluster.starclustercfg import *

log = logging.getLogger()

def setup_cluster_user(nodes):
    log.info(">>> Creating cluster user: %s" % CLUSTER_USER)
    for node in nodes:
        nconn = node['CONNECTION']
        nconn.execute('useradd -m -s /bin/bash %s' % CLUSTER_USER)

def setup_scratch(nodes):
    log.info(">>> Configuring scratch space for user: %s" % CLUSTER_USER)
    for node in nodes:
        nconn = node['CONNECTION']
        nconn.execute('mkdir /mnt/%s' % CLUSTER_USER)
        nconn.execute('chown -R %(user)s:%(user)s /mnt/%(user)s' % {'user':CLUSTER_USER})
        nconn.execute('mkdir /scratch')
        nconn.execute('ln -s /mnt/%s /scratch' % CLUSTER_USER)

def setup_etc_hosts(nodes):
    log.info(">>> Configuring /etc/hosts on each node")
    #host_file = tempfile.NamedTemporaryFile()
    #fd = host_file.file
    #print >> fd, "# Do not remove the following line or programs that require network functionality will fail"
    #print >> fd, "127.0.0.1 localhost.localdomain localhost"
    #for node in nodes:
        #print >> fd, "%(INTERNAL_IP)s %(INTERNAL_NAME)s %(INTERNAL_NAME_SHORT)s %(INTERNAL_ALIAS)s" % node 
    #fd.close()
    #for node in nodes:
        #node['CONNECTION'].put(host_file.name,'/etc/hosts')

    for node in nodes:
        conn = node['CONNECTION']
        host_file = conn.remote_file('/etc/hosts')
        print >> host_file, "# Do not remove the following line or programs that require network functionality will fail"
        print >> host_file, "127.0.0.1 localhost.localdomain localhost"
        for node in nodes:
            print >> host_file, "%(INTERNAL_IP)s %(INTERNAL_NAME)s %(INTERNAL_NAME_SHORT)s %(INTERNAL_ALIAS)s" % node 
        host_file.close()

def setup_passwordless_ssh(nodes):
    log.info(">>> Configuring passwordless ssh for root")
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

    log.info(">>> Configuring passwordless ssh for user: %s" % CLUSTER_USER)
    # only needed on master, nfs takes care of the rest
    mconn.execute('cp -r /root/.ssh /home/%s/' % CLUSTER_USER)
    mconn.execute('chown -R %(user)s:%(user)s /home/%(user)s/.ssh' % {'user':CLUSTER_USER})

def setup_ebs_volume(nodes):
    # setup /etc/fstab on master to use block device if specified
    if globals().has_key('ATTACH_VOLUME') and globals().has_key('VOLUME_PARTITION'):
        if ATTACH_VOLUME is not None and VOLUME_PARTITION is not None:
            mconn = nodes[0]['CONNECTION']
            master_fstab = mconn.remote_file('/etc/fstab', mode='a')
            print >> master_fstab, "%s /home ext3 noauto,defaults 0 0 " % VOLUME_PARTITION
            master_fstab.close()
            mconn.execute('mount /home')

def setup_nfs(nodes):
    log.info(">>> Configuring NFS...")

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
    log.info(">>> Configuring Sun Grid Engine...")

    # generate /etc/profile.d/sge.sh for each node
    for node in nodes:
        conn = node['CONNECTION']
        sge_profile = conn.remote_file("/etc/profile.d/sge.sh")
        arch = conn.execute("/opt/sge6/util/arch")[0]

        print >> sge_profile, """
export SGE_ROOT="/opt/sge6"
export SGE_CELL="default"
export SGE_CLUSTER_NAME="starcluster"
export SGE_QMASTER_PORT="63231"
export SGE_EXECD_PORT="63232"
export MANTYPE="man"
export MANPATH="$MANPATH/opt/sge6/man"
export PATH="$PATH:/opt/sge6/bin/%(arch)s"
export ROOTPATH="$ROOTPATH:/opt/sge6/bin/%(arch)s"
export LDPATH="$LDPATH:/opt/sge6/lib/%(arch)s"
        """ % {'arch': arch}
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
    print >> ec2_sge_conf, """
SGE_CLUSTER_NAME="starcluster"
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
ADMIN_MAIL="none@none.edu"
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
CSP_STATE="MA"
CSP_LOCATION="BOSTON"
CSP_ORGA="MIT"
CSP_ORGA_UNIT="OEIT"
CSP_MAIL_ADDRESS="none@none.edu"
    """ % (admin_list, exec_list, submit_list)
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
    print >> parallel_environment, """
pe_name           orte
slots             %s
user_lists        NONE
xuser_lists       NONE
start_proc_args   /bin/true
stop_proc_args    /bin/true
allocation_rule   $round_robin
control_slaves    TRUE
job_is_first_task FALSE
urgency_slots     min
accounting_summary FALSE
    """ % num_processors
    parallel_environment.close()
    mconn.execute("source /etc/profile && qconf -Ap %s" % parallel_environment.name)

    mconn.execute('source /etc/profile && qconf -mattr queue pe_list "orte" all.q')
    #mconn.execute("source /etc/profile && qconf -sq all.q > /tmp/allq.txt")
    #allq_file = mconn.remote_file("/tmp/allq.txt","r")
    #allq_file_lines = allq_file.readlines()
    #allq_file.close()

    #new_allq_file_lines = []
    #for line in allq_file_lines:
        #if line.startswith('pe_list'):
            #line = 'pe_list make orte\n'
        #new_allq_file_lines.append(line)

    #allq_file = mconn.remote_file("/tmp/allq.txt","w")
    #allq_file.writelines(new_allq_file_lines)
    #allq_file.close()
    #mconn.execute("source /etc/profile && qconf -Mq %s" % allq_file.name)

    #todo cleanup /tmp/pe.txt and /tmp/allq.txt
    log.info(">>> Done Configuring Sun Grid Engine")

def main(nodes):
    setup_ebs_volume(nodes)
    setup_cluster_user(nodes)
    setup_scratch(nodes)
    setup_etc_hosts(nodes)
    setup_nfs(nodes)
    setup_passwordless_ssh(nodes)
    setup_sge(nodes)
