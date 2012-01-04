"""
clustersetup.py
"""
import re
import posixpath

from starcluster import threadpool
from starcluster.utils import print_timing
from starcluster.templates import sge
from starcluster.logger import log


class ClusterSetup(object):
    """
    ClusterSetup Interface

    This is the base class for all StarCluster plugins. A plugin should
    implement at least one if not all of these methods.
    """
    def __init__(self, *args, **kwargs):
        pass

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        """
        This methods gets executed after a node has been added to the cluster
        """
        raise NotImplementedError('on_add_node method not implemented')

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        """
        This method gets executed before a node is about to be removed from the
        cluster
        """
        raise NotImplementedError('on_remove_node method not implemented')

    def on_restart(self, nodes, master, user, user_shell, volumes):
        """
        This method gets executed before restart the cluster
        """
        raise NotImplementedError('on_restart method not implemented')

    def on_shutdown(self, nodes, master, user, user_shell, volumes):
        """
        This method gets executed before shutting down the cluster
        """
        raise NotImplementedError('on_shutdown method not implemented')

    def run(self, nodes, master, user, user_shell, volumes):
        """
        Run this plugin's setup routines

        This method gets executed after the default cluster setup routines have
        been performed
        """
        raise NotImplementedError('run method not implemented')


class DefaultClusterSetup(ClusterSetup):
    """
    Default ClusterSetup implementation for StarCluster
    """
    def __init__(self, disable_queue=False, disable_threads=False,
                 num_threads=20):
        self._nodes = None
        self._master = None
        self._user = None
        self._user_shell = None
        self._volumes = None
        self._disable_queue = disable_queue
        self._disable_threads = disable_threads
        self._num_threads = num_threads
        self._pool = None

    @property
    def pool(self):
        if not self._pool:
            self._pool = threadpool.get_thread_pool(self._num_threads,
                                                    self._disable_threads)
        return self._pool

    @property
    def nodes(self):
        return filter(lambda x: not x.is_master(), self._nodes)

    @property
    def running_nodes(self):
        return filter(lambda x: x.state in ['running'], self._nodes)

    def _setup_hostnames(self, nodes=None):
        """
        Set each node's hostname to their alias.
        """
        nodes = nodes or self._nodes
        log.info("Configuring hostnames...")
        for node in nodes:
            self.pool.simple_job(node.set_hostname, (), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def _setup_cluster_user(self):
        """
        Create cluster user on all StarCluster nodes

        This command takes care to examine existing folders in /home
        and set the new cluster_user's uid/gid accordingly. This is necessary
        for the case of EBS volumes containing /home with large amounts of data
        in them. It's much less expensive in this case to set the uid/gid of
        the new user to be the existing uid/gid of the dir in EBS rather than
        chowning potentially terabytes of data.
        """
        mconn = self._master.ssh
        home_folder = '/home/%s' % self._user
        first_uid = 1000
        uid, gid = first_uid, first_uid
        umap = self._master.get_user_map(key_by_uid=True)
        if mconn.path_exists(home_folder):
            # get /home/user's owner/group uid and create
            # user with that uid/gid
            s = mconn.stat(home_folder)
            uid = s.st_uid
            gid = s.st_gid
        else:
            # get highest uid/gid of dirs in /home/*,
            # increment by 1 and create user with that uid/gid
            uid_db = {}
            files = mconn.ls('/home')
            for file in files:
                if mconn.isdir(file):
                    f = mconn.stat(file)
                    uid_db[f.st_uid] = (file, f.st_gid)
            if uid_db.keys():
                max_uid = max(uid_db.keys())
                max_gid = uid_db[max_uid][1]
                uid, gid = max_uid + 1, max_gid + 1
                # make sure the newly selected uid/gid is >= 1000
                uid = max(uid, first_uid)
                gid = max(gid, first_uid)
            # make sure newly selected uid is not already in /etc/passwd
            while umap.get(uid):
                uid += 1
                gid += 1
        log.info("Creating cluster user: %s (uid: %d, gid: %d)" % (self._user,
                                                                   uid, gid))
        self._add_user_to_nodes(uid, gid, self._nodes)

    def _add_user_to_node(self, uid, gid, node):
        existing_user = node.getpwuid(uid)
        if existing_user:
            username = existing_user.pw_name
            if username != self._user:
                msg = ("user %s exists on %s with same uid/gid as "
                       "cluster user %s...removing user %s")
                log.debug(
                    msg % (username, node.alias, self._user, username))
                node.remove_user(username)
                node.add_user(self._user, uid, gid, self._user_shell)
            log.debug("user %s exists on node %s, no action" %
                      (self._user, node.alias))
        else:
            log.debug("user %s does not exist, creating..." % self._user)
            node.add_user(self._user, uid, gid, self._user_shell)

    def _add_user_to_nodes(self, uid, gid, nodes=None):
        nodes = nodes or self._nodes
        for node in nodes:
            self.pool.simple_job(self._add_user_to_node, (uid, gid, node),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def _setup_scratch_on_node(self, node):
        nconn = node.ssh
        user_scratch = '/mnt/%s' % self._user
        if not nconn.path_exists(user_scratch):
            nconn.mkdir(user_scratch)
        nconn.execute('chown -R %(user)s:%(user)s /mnt/%(user)s' %
                      {'user': self._user})
        scratch = '/scratch'
        if not nconn.path_exists(scratch):
            nconn.mkdir(scratch)
        if not nconn.path_exists(posixpath.join(scratch, self._user)):
            nconn.execute('ln -s %s %s' % (user_scratch, scratch))

    def _setup_scratch(self, nodes=None):
        """ Configure scratch space on all StarCluster nodes """
        log.info("Configuring scratch space for user: %s" % self._user)
        nodes = nodes or self._nodes
        for node in nodes:
            self.pool.simple_job(self._setup_scratch_on_node, (node,),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def _setup_etc_hosts(self, nodes=None):
        """ Configure /etc/hosts on all StarCluster nodes"""
        log.info("Configuring /etc/hosts on each node")
        nodes = nodes or self._nodes
        for node in nodes:
            self.pool.simple_job(node.add_to_etc_hosts, (nodes, ),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def _setup_passwordless_ssh(self, nodes=None):
        """
        Properly configure passwordless ssh for root and CLUSTER_USER on all
        StarCluster nodes
        """
        log.info("Configuring passwordless ssh for root")
        master = self._master
        nodes = nodes or self.nodes
        master.generate_key_for_user('root', auth_new_key=True,
                                     auth_conn_key=True)
        master.enable_passwordless_ssh('root', nodes)
        # generate public/private keys, authorized_keys, and known_hosts files
        # for cluster_user once on master node...NFS takes care of the rest
        log.info("Configuring passwordless ssh for %s" % self._user)
        master.generate_key_for_user(self._user, auth_new_key=True,
                                     auth_conn_key=True)
        master.add_to_known_hosts(self._user, nodes)

    def _setup_ebs_volumes(self):
        """
        Mount EBS volumes, if specified in ~/.starcluster/config to /home
        """
        # setup /etc/fstab on master to use block device if specified
        master = self._master
        devs = master.ssh.ls('/dev')
        for vol in self._volumes:
            vol = self._volumes[vol]
            vol_id = vol.get("volume_id")
            mount_path = vol.get('mount_path')
            device = vol.get("device")
            volume_partition = vol.get('partition')
            if not (vol_id and device and mount_path):
                log.error("missing required settings for vol %s" % vol)
                continue
            dev_exists = master.ssh.path_exists(device)
            if not dev_exists and device.startswith('/dev/sd'):
                # check for "correct" device in unpatched kernels
                device = device.replace('/dev/sd', '/dev/xvd')
                dev_exists = master.ssh.path_exists(device)
            if not dev_exists:
                log.warn("Cannot find device %s for volume %s" %
                         (device, vol_id))
                log.warn("Not mounting %s on %s" % (vol_id, mount_path))
                log.warn("This usually means there was a problem "
                         "attaching the EBS volume to the master node")
                continue
            if not volume_partition:
                partitions = filter(lambda x: x.startswith(device), devs)
                if len(partitions) == 1:
                    volume_partition = device
                elif len(partitions) == 2:
                    volume_partition = device + '1'
                else:
                    log.error(
                        "volume has more than one partition, please specify "
                        "which partition to use (e.g. partition=0, "
                        "partition=1, etc.) in the volume's config")
                    continue
            elif not master.ssh.path_exists(volume_partition):
                log.warn("Cannot find partition %s on volume %s" %
                         (volume_partition, vol_id))
                log.warn("Not mounting %s on %s" % (vol_id,
                                                    mount_path))
                log.warn("This either means that the volume has not "
                         "been partitioned or that the partition"
                         "specified does not exist on the volume")
                continue
            log.info("Mounting EBS volume %s on %s..." % (vol_id, mount_path))
            mount_map = self._master.get_mount_map()
            dev = mount_map.get(volume_partition)
            if dev:
                path, fstype, options = dev
                if path != mount_path:
                    log.error("Volume %s is mounted on %s, not on %s" %
                              (vol_id, path, mount_path))
                else:
                    log.info(
                        "Volume %s already mounted on %s...skipping" %
                        (vol_id, mount_path))
                continue
            self._master.mount_device(volume_partition, mount_path)

    def _get_nfs_export_paths(self):
        export_paths = ['/home']
        if not self._disable_queue:
            export_paths.append('/opt/sge6')
        for vol in self._volumes:
            vol = self._volumes[vol]
            mount_path = vol.get('mount_path')
            if not mount_path in export_paths:
                export_paths.append(mount_path)
        return export_paths

    def _mount_nfs_shares(self, nodes):
        # setup /etc/fstab and mount each nfs share on each node
        master = self._master
        export_paths = self._get_nfs_export_paths()
        for node in nodes:
            mount_map = node.get_mount_map()
            mount_paths = []
            for path in export_paths:
                network_device = "%s:%s" % (master.alias, path)
                if network_device in mount_map:
                    mount_path, type, options = mount_map.get(network_device)
                    log.debug('nfs share %s already mounted to %s on '
                              'node %s, skipping...' %
                              (network_device, mount_path, node.alias))
                else:
                    mount_paths.append(path)
            self.pool.simple_job(node.mount_nfs_shares, (master, mount_paths),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    @print_timing("Setting up NFS")
    def _setup_nfs(self, nodes=None, start_server=True):
        """
        Share /home, /opt/sge6, and all EBS mount paths via NFS to all nodes
        """
        log.info("Configuring NFS...")
        master = self._master
        if not self._disable_queue and not master.ssh.isdir('/opt/sge6'):
            # copy fresh sge installation files to /opt/sge6
            master.ssh.execute('cp -r /opt/sge6-fresh /opt/sge6')
            master.ssh.execute('chown -R %(user)s:%(user)s /opt/sge6' %
                               {'user': self._user})
        # setup /etc/exports and start nfsd on master node
        nodes = nodes or self.nodes
        export_paths = self._get_nfs_export_paths()
        if start_server:
            master.start_nfs_server()
        master.export_fs_to_nodes(nodes, export_paths)
        self._mount_nfs_shares(nodes)

    def _create_sge_pe(self, name="orte", nodes=None, queue="all.q"):
        """
        Create or update an SGE parallel environment

        name - name of parallel environment
        nodes - list of nodes to include in the parallel environment
                (default: all)
        queue - configure queue to use the new parallel environment
        """
        mssh = self._master.ssh
        pe_exists = mssh.get_status('qconf -sp %s' % name, source_profile=True)
        pe_exists = pe_exists == 0
        if not pe_exists:
            log.info("Creating SGE parallel environment '%s'" % name)
        else:
            log.info("Updating SGE parallel environment '%s'" % name)
        # iterate through each machine and count the number of processors
        nodes = nodes or self._nodes
        num_processors = sum(self.pool.map(lambda n: n.num_processors, nodes))
        penv = mssh.remote_file("/tmp/pe.txt")
        print >> penv, sge.sge_pe_template % (name, num_processors)
        penv.close()
        if not pe_exists:
            mssh.execute("qconf -Ap %s" % penv.name, source_profile=True)
        else:
            mssh.execute("qconf -Mp %s" % penv.name, source_profile=True)
        if queue:
            log.info("Adding parallel environment '%s' to queue '%s'" %
                     (name, queue))
            mssh.execute('qconf -mattr queue pe_list "%s" %s' % (name, queue),
                         source_profile=True)

    def _setup_sge(self):
        """
        Install Sun Grid Engine with a default parallel
        environment on StarCluster
        """
        # generate /etc/profile.d/sge.sh for each node
        for node in self._nodes:
            conn = node.ssh
            conn.execute('pkill -9 sge', ignore_exit_status=True)
            conn.execute('rm /etc/init.d/sge*', ignore_exit_status=True)
            sge_profile = conn.remote_file("/etc/profile.d/sge.sh")
            arch = conn.execute("/opt/sge6/util/arch")[0]
            print >> sge_profile, sge.sgeprofile_template % {'arch': arch}
            sge_profile.close()
        # setup sge auto install file
        master = self._master
        default_cell = '/opt/sge6/default'
        if master.ssh.isdir(default_cell):
            log.info("Removing previous SGE installation...")
            master.ssh.execute('rm -rf %s' % default_cell)
            master.ssh.execute('exportfs -fra')
        mconn = master.ssh
        admin_list = ' '.join(map(lambda n: n.alias, self._nodes))
        exec_list = admin_list
        submit_list = admin_list
        ec2_sge_conf = mconn.remote_file("/opt/sge6/ec2_sge.conf")
        # TODO: add sge section to config values for some of the below
        conf = sge.sgeinstall_template % (admin_list, exec_list, submit_list)
        print >> ec2_sge_conf, conf
        ec2_sge_conf.close()
        # installs sge in /opt/sge6 and starts qmaster/schedd on master node
        log.info("Installing Sun Grid Engine...")
        mconn.execute('cd /opt/sge6 && TERM=rxvt ./inst_sge -m -x -noremote '
                      '-auto ./ec2_sge.conf', silent=True, only_printable=True)
        # set all.q shell to bash
        mconn.execute('qconf -mattr queue shell "/bin/bash" all.q',
                      source_profile=True)
        for node in self.nodes:
            self._add_sge_administrative_host(node)
            self._add_sge_submit_host(node)
            self.pool.simple_job(self._add_to_sge, (node,), jobid=node.alias)
        self.pool.wait(numtasks=len(self.nodes))
        self._create_sge_pe()

    def run(self, nodes, master, user, user_shell, volumes):
        """Start cluster configuration"""
        try:
            self._nodes = nodes
            self._master = master
            self._user = user
            self._user_shell = user_shell
            self._volumes = volumes
            self._setup_hostnames()
            self._setup_ebs_volumes()
            self._setup_cluster_user()
            self._setup_scratch()
            self._setup_etc_hosts()
            self._setup_nfs()
            self._setup_passwordless_ssh()
            if not self._disable_queue:
                self._setup_sge()
        finally:
            self.pool.shutdown()

    def _remove_from_etc_hosts(self, node):
        nodes = filter(lambda x: x.id != node.id, self.running_nodes)
        for n in nodes:
            n.remove_from_etc_hosts([node])

    def _remove_nfs_exports(self, node):
        self._master.stop_exporting_fs_to_nodes([node])

    def _remove_from_known_hosts(self, node):
        nodes = filter(lambda x: x.id != node.id, self.running_nodes)
        for n in nodes:
            n.remove_from_known_hosts('root', [node])
            n.remove_from_known_hosts(self._user, [node])

    def _remove_from_sge(self, node):
        master = self._master
        master.ssh.execute('qconf -shgrp @allhosts > /tmp/allhosts',
                           source_profile=True)
        hgrp_file = master.ssh.remote_file('/tmp/allhosts', 'r')
        contents = hgrp_file.read().splitlines()
        hgrp_file.close()
        c = []
        for line in contents:
            line = line.replace(node.alias, '')
            c.append(line)
        hgrp_file = master.ssh.remote_file('/tmp/allhosts_new', 'w')
        hgrp_file.writelines('\n'.join(c))
        hgrp_file.close()
        master.ssh.execute('qconf -Mhgrp /tmp/allhosts_new',
                           source_profile=True)
        master.ssh.execute('qconf -sq all.q > /tmp/allq', source_profile=True)
        allq_file = master.ssh.remote_file('/tmp/allq', 'r')
        contents = allq_file.read()
        allq_file.close()
        c = [l.strip() for l in contents.splitlines()]
        s = []
        allq = []
        for l in c:
            if l.startswith('slots') or l.startswith('['):
                s.append(l)
            else:
                allq.append(l)
        regex = re.compile(r"\[%s=\d+\],?" % node.alias)
        slots = []
        for line in s:
            line = line.replace('\\', '')
            slots.append(regex.sub('', line))
        allq.append(''.join(slots))
        f = master.ssh.remote_file('/tmp/allq_new', 'w')
        allq[-1] = allq[-1].strip()
        if allq[-1].endswith(','):
            allq[-1] = allq[-1][:-1]
        f.write('\n'.join(allq))
        f.close()
        master.ssh.execute('qconf -Mq /tmp/allq_new', source_profile=True)
        master.ssh.execute('qconf -dconf %s' % node.alias, source_profile=True)
        master.ssh.execute('qconf -de %s' % node.alias, source_profile=True)
        node.ssh.execute('pkill -9 sge_execd')
        nodes = filter(lambda n: n.alias != node.alias, self._nodes)
        self._create_sge_pe(nodes=nodes)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Removing node %s (%s)..." % (node.alias, node.id))
        if not self._disable_queue:
            log.info("Removing %s from SGE" % node.alias)
            self._remove_from_sge(node)
        log.info("Removing %s from known_hosts files" % node.alias)
        self._remove_from_known_hosts(node)
        log.info("Removing %s from /etc/hosts" % node.alias)
        self._remove_from_etc_hosts(node)
        log.info("Removing %s from NFS" % node.alias)
        self._remove_nfs_exports(node)

    def _create_user(self, node):
        user = self._master.getpwnam(self._user)
        uid, gid = user.pw_uid, user.pw_gid
        self._add_user_to_nodes(uid, gid, nodes=[node])

    def _add_sge_submit_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -as %s' % node.alias, source_profile=True)

    def _add_sge_administrative_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -ah %s' % node.alias, source_profile=True)

    def _add_to_sge(self, node):
        # generate /etc/profile.d/sge.sh
        sge_profile = node.ssh.remote_file("/etc/profile.d/sge.sh")
        arch = node.ssh.execute("/opt/sge6/util/arch")[0]
        print >> sge_profile, sge.sgeprofile_template % {'arch': arch}
        sge_profile.close()
        node.ssh.execute('cd /opt/sge6 && TERM=rxvt ./inst_sge -x -noremote '
                         '-auto ./ec2_sge.conf')

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        self._setup_hostnames(nodes=[node])
        self._setup_etc_hosts(nodes)
        self._setup_nfs(nodes=[node], start_server=False)
        self._create_user(node)
        self._setup_scratch(nodes=[node])
        self._setup_passwordless_ssh(nodes=[node])
        if not self._disable_queue:
            log.info("Adding %s to SGE" % node.alias)
            self._add_sge_administrative_host(node)
            self._add_sge_submit_host(node)
            self._add_to_sge(node)
            self._create_sge_pe()
