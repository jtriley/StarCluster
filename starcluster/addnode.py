import os
import time
from starcluster.spinner import Spinner
from starcluster.templates.sgeprofile import sgeprofile_template
from starcluster.logger import log, INFO_NO_NEWLINE

def create_user(cluster, node):
    s = cluster.master_node.ssh.stat(os.path.join('/home',
                                                  cluster.cluster_user))
    uid = s.st_uid
    gid = s.st_gid
    nconn = node.ssh
    nconn.execute('groupadd -o -g %s %s' % (gid, cluster.cluster_user))
    nconn.execute('useradd -o -u %s -g %s -m -s `which %s` %s' %
                  (uid, gid, cluster.cluster_shell, cluster.cluster_user))

def setup_passwordless_ssh(cluster, node):
    master = cluster.master_node
    root_rsa = master.ssh.remote_file('/root/.ssh/id_rsa')
    root_pubkey = master.ssh.remote_file('/root/.ssh/id_rsa.pub')
    rsa = root_rsa.read()
    root_rsa.close()
    pubkey = root_pubkey.read()
    root_pubkey.close()
    root_rsa = node.ssh.remote_file('/root/.ssh/id_rsa')
    root_rsa.write(rsa)
    root_rsa.close()
    root_pubkey = node.ssh.remote_file('/root/.ssh/id_rsa.pub')
    root_pubkey.write(pubkey)
    root_pubkey.close()
    node.ssh.execute('cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys')

def add_to_sge(master,node):
    # generate /etc/profile.d/sge.sh
    sge_profile = node.ssh.remote_file("/etc/profile.d/sge.sh")
    arch = node.ssh.execute("/opt/sge6/util/arch")[0]
    print >> sge_profile, sgeprofile_template  % {'arch': arch}
    sge_profile.close()
    master.ssh.execute('source /etc/profile && qconf -ah %s' %
                       node.private_dns_name)
    master.ssh.execute('source /etc/profile && qconf -as %s' %
                       node.private_dns_name)
    node.ssh.execute('cd /opt/sge6 && TERM=rxvt ./inst_sge -x -noremote -auto ./ec2_sge.conf')

def setup_etc_exports(cluster, node):
    m = cluster.master_node
    exports = m.ssh.remote_file('/etc/exports','r')
    etc_exports = exports.readlines()
    exports.close()
    nfs_export_settings = "(async,no_root_squash,no_subtree_check,rw)"
    # still need to handle rest of EBS vols specified
    etc_exports.append('/home ' + node.private_dns_name + nfs_export_settings +
                       '\n')
    etc_exports.append('/opt/sge6 ' + node.private_dns_name +
                       nfs_export_settings + '\n')
    exports = m.ssh.remote_file('/etc/exports')
    exports.writelines(etc_exports)
    m.ssh.execute('exportfs -a')

def mount_nfs(cluster, node):
    master = cluster.master_node
    nconn = node.ssh
    nconn.execute('/etc/init.d/portmap start')
    nconn.execute('mkdir /opt/sge6')
    nconn.execute('chown -R %(user)s:%(user)s /opt/sge6' %
                  {'user':cluster.cluster_user})
    nconn.execute('echo "%s:/home /home nfs user,rw,exec 0 0" >> /etc/fstab' %
                  master.private_dns_name)
    nconn.execute(
        'echo "%s:/opt/sge6 /opt/sge6 nfs user,rw,exec 0 0" >> /etc/fstab' %
                  master.private_dns_name)
    nconn.execute('mount /home')
    nconn.execute('mount /opt/sge6')
    # fix for xterm
    nconn.execute('mount -t devpts none /dev/pts', ignore_exit_status=True)

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

def add_node(cluster, node):
    master = cluster.master_node
    setup_etc_hosts(cluster)
    create_user(cluster, node)
    setup_etc_exports(cluster,node)
    mount_nfs(cluster,node)
    add_to_sge(master, node)

def add_nodes(cluster, num_nodes):
    cluster.load_receipt()
    current_num_nodes = len([i for i in cluster.cluster_group.instances() if i.state in ['pending','running']])
    new_nodes = []
    for id in range(current_num_nodes, current_num_nodes + num_nodes):
        alias = 'node%.3d' % id
        print cluster.create_node(alias)
        new_nodes.append(alias)
    print new_nodes
    cluster.cluster_size = current_num_nodes + num_nodes
    cluster._nodes = None
    s = Spinner()
    log.log(INFO_NO_NEWLINE, "Waiting for nodes to come up...")
    while not cluster.is_cluster_up():
        cluster._nodes = None
        time.sleep(30)
    s.stop()
    for alias in new_nodes:
        node = cluster.get_node_by_alias(alias)
        add_node(cluster, node)
