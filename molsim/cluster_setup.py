#!/usr/bin/env python

"""
create_hosts.py
"""

import os
import tempfile

from molsim.molsimcfg import CLUSTER_USER, KEY_LOCATION

def setup_etc_hosts(nodes):
    host_file = tempfile.NamedTemporaryFile()
    fd = host_file.file
    print >> fd, "# Do not remove the following line or programs that require network functionality will fail"
    print >> fd, "127.0.0.1 localhost.localdomain localhost"
    for node in nodes:
        print >> fd, "%(INTERNAL_IP)s %(INTERNAL_NAME)s %(INTERNAL_NAME_SHORT)s %(INTERNAL_ALIAS)s" % node 
    fd.close()
    for node in nodes:
        node['CONNECTION'].put(host_file.name,'/etc/hosts')
    #host_file.unlink(host_file.name)

def setup_passwordless_ssh(nodes):
    print ">>> Configuring passwordless ssh for root"
    for node in nodes:
        conn = node['CONNECTION']
        conn.put(KEY_LOCATION,'/root/.ssh/id_rsa')
        conn.execute('chmod 400 /root/.ssh/id_rsa')

    print ">>> Configuring passwordless ssh for user: %s" % CLUSTER_USER
    # only needed on master, nfs takes care of the rest
    master = nodes[0]
    conn = master['CONNECTION']
    print conn.execute('cp -r /root/.ssh /home/%s/' % CLUSTER_USER)
    print conn.execute('chown -R %(user)s:%(user)s /home/%(user)s/.ssh' % {'user':CLUSTER_USER})

def setup_nfs(nodes):
    print ">>> Configuring NFS..."

    master = nodes[0]
    mconn = master['CONNECTION']

    print mconn.execute('rm -rf /opt/sge6')
    print mconn.execute('cp -r /opt/sge6-fresh /opt/sge6')

    print mconn.execute('chown -R %(user)s:%(user)s /opt/sge6' % {'user': CLUSTER_USER})

    # setup /etc/exports and start nfsd on master node
    nfs_export_settings = "(async,no_root_squash,no_subtree_check,rw)"
    etc_exports = mconn.remote_file('/etc/exports')
    for node in nodes:
        if node['NODE_ID'] != 0:
            etc_exports.write('/home/ ' + node['INTERNAL_NAME'] + nfs_export_settings + '\n')
            etc_exports.write('/opt/sge6 ' + node['INTERNAL_NAME'] + nfs_export_settings + '\n')
    etc_exports.close()
    
    print mconn.execute('/etc/init.d/portmap start')
    print mconn.execute('mount -t rpc_pipefs sunrpc /var/lib/nfs/rpc_pipefs/')
    print mconn.execute('/etc/init.d/nfs start')
    print mconn.execute('/usr/sbin/exportfs -r')
    print mconn.execute('mount -t devpts none /dev/pts')

    # setup /etc/fstab and mount /opt/sge6 on each node
    for node in nodes:
        if node['NODE_ID'] != 0:
            nconn = node['CONNECTION']
            print nconn.execute('/etc/init.d/portmap start')
            print nconn.execute('echo "%s:/home /home nfs user,rw,exec 0 0" >> /etc/fstab' % master['INTERNAL_NAME'])
            print nconn.execute('echo "%s:/opt/sge6 /opt/sge6 nfs user,rw,exec 0 0" >> /etc/fstab' % master['INTERNAL_NAME'])
            print nconn.execute('mount /home')
            print nconn.execute('mount /opt/sge6')
            print nconn.execute('mount -t devpts none /dev/pts') # fix for xterm


def setup_sge(nodes):
    print ">>> Configuring Sun Grid Engine..."

    master = nodes[0]
    mconn = master['CONNECTION']

    admin_list = ''
    for node in nodes:
        admin_list = admin_list + " " +node['INTERNAL_NAME']

    exec_list = admin_list
    submit_list = admin_list
    ec2_sge_conf = mconn.remote_file("/opt/sge6/ec2_sge.conf")

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

    # installs sge in /opt/sge6 and starts qmaster and schedd on master node
    mconn.execute('cd /opt/sge6 && TERM=rxvt ./inst_sge -m -x -auto ec2_sge.conf')

def main(nodes):
    setup_etc_hosts(nodes)
    setup_passwordless_ssh(nodes)
    setup_nfs(nodes)
    setup_sge(nodes)
