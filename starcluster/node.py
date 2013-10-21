# Copyright 2009-2013 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import re
import time
import stat
import base64
import posixpath
import subprocess

from starcluster import utils
from starcluster import static
from starcluster import sshutils
from starcluster import awsutils
from starcluster import managers
from starcluster import userdata
from starcluster import exception
from starcluster.logger import log


class NodeManager(managers.Manager):
    """
    Manager class for Node objects
    """
    def ssh_to_node(self, node_id, user='root', command=None,
                    forward_x11=False, forward_agent=False):
        node = self.get_node(node_id, user=user)
        return node.shell(user=user, command=command, forward_x11=forward_x11,
                          forward_agent=forward_agent)

    def get_node(self, node_id, user='root'):
        """Factory for Node class"""
        instances = self.ec2.get_all_instances()
        node = None
        for instance in instances:
            if instance.dns_name == node_id:
                node = instance
                break
            elif instance.id == node_id:
                node = instance
                break
        if not node:
            raise exception.InstanceDoesNotExist(node_id)
        key = self.cfg.get_key(node.key_name)
        node = Node(node, key.key_location, user=user)
        return node


class Node(object):
    """
    This class represents a single compute node in a StarCluster.

    It contains all useful metadata for the node such as the internal/external
    hostnames, ips, etc. as well as an ssh object for executing commands,
    creating/modifying files on the node.

    'instance' arg must be an instance of boto.ec2.instance.Instance

    'key_location' arg is a string that contains the full path to the
    private key corresponding to the keypair used to launch this node

    'alias' keyword arg optionally names the node. If no alias is provided,
    the alias is retrieved from the node's user_data based on the node's
    launch index

    'user' keyword optionally specifies user to ssh as (defaults to root)
    """
    def __init__(self, instance, key_location, alias=None, user='root'):
        self.instance = instance
        self.ec2 = awsutils.EasyEC2(instance.connection.aws_access_key_id,
                                    instance.connection.aws_secret_access_key,
                                    connection=instance.connection)
        self.key_location = key_location
        self.user = user
        self._alias = alias
        self._groups = None
        self._ssh = None
        self._num_procs = None
        self._memory = None
        self._user_data = None

    def __repr__(self):
        return '<Node: %s (%s)>' % (self.alias, self.id)

    def _get_user_data(self, tries=5):
        tries = range(tries)
        last_try = tries[-1]
        for i in tries:
            try:
                user_data = self.ec2.get_instance_user_data(self.id)
                return user_data
            except exception.InstanceDoesNotExist:
                if i == last_try:
                    log.debug("failed fetching user data")
                    raise
                log.debug("InvalidInstanceID.NotFound: "
                          "retrying fetching user data (tries: %s)" % (i + 1))
                time.sleep(5)

    @property
    def user_data(self):
        if not self._user_data:
            try:
                raw = self._get_user_data()
                self._user_data = userdata.unbundle_userdata(raw)
            except IOError, e:
                parent_cluster = self.parent_cluster
                if self.parent_cluster:
                    raise exception.IncompatibleCluster(parent_cluster)
                else:
                    raise exception.BaseException(
                        "Error occurred unbundling userdata: %s" % e)
        return self._user_data

    @property
    def alias(self):
        """
        Fetches the node's alias stored in a tag from either the instance
        or the instance's parent spot request. If no alias tag is found an
        exception is raised.
        """
        if not self._alias:
            alias = self.tags.get('alias')
            if not alias:
                aliasestxt = self.user_data.get(static.UD_ALIASES_FNAME)
                aliases = aliasestxt.splitlines()[2:]
                index = self.ami_launch_index
                try:
                    alias = aliases[index]
                except IndexError:
                    alias = None
                    log.debug("invalid aliases file in user_data:\n%s" %
                              aliasestxt)
                if not alias:
                    raise exception.BaseException(
                        "instance %s has no alias" % self.id)
                self.add_tag('alias', alias)
            if not self.tags.get('Name'):
                self.add_tag('Name', alias)
            self._alias = alias
        return self._alias

    def get_plugins(self):
        plugstxt = self.user_data.get(static.UD_PLUGINS_FNAME)
        payload = plugstxt.split('\n', 2)[2]
        plugins_metadata = utils.decode_uncompress_load(payload)
        plugs = []
        for klass, args, kwargs in plugins_metadata:
            mod_path, klass_name = klass.rsplit('.', 1)
            try:
                mod = __import__(mod_path, fromlist=[klass_name])
                plug = getattr(mod, klass_name)(*args, **kwargs)
            except SyntaxError, e:
                raise exception.PluginSyntaxError(
                    "Plugin %s (%s) contains a syntax error at line %s" %
                    (klass_name, e.filename, e.lineno))
            except ImportError, e:
                raise exception.PluginLoadError(
                    "Failed to import plugin %s: %s" %
                    (klass_name, e[0]))
            except Exception as exc:
                log.error("Error occured:", exc_info=True)
                raise exception.PluginLoadError(
                    "Failed to load plugin %s with "
                    "the following error: %s - %s" %
                    (klass_name, exc.__class__.__name__, exc.message))
            plugs.append(plug)
        return plugs

    def get_volumes(self):
        volstxt = self.user_data.get(static.UD_VOLUMES_FNAME)
        payload = volstxt.split('\n', 2)[2]
        return utils.decode_uncompress_load(payload)

    def _remove_all_tags(self):
        tags = self.tags.keys()[:]
        for t in tags:
            self.remove_tag(t)

    @property
    def tags(self):
        return self.instance.tags

    def add_tag(self, key, value=None):
        return self.instance.add_tag(key, value)

    def remove_tag(self, key, value=None):
        return self.instance.remove_tag(key, value)

    @property
    def groups(self):
        if not self._groups:
            groups = map(lambda x: x.name, self.instance.groups)
            self._groups = self.ec2.get_all_security_groups(groupnames=groups)
        return self._groups

    @property
    def cluster_groups(self):
        sg_prefix = static.SECURITY_GROUP_PREFIX
        return filter(lambda x: x.name.startswith(sg_prefix), self.groups)

    @property
    def parent_cluster(self):
        try:
            return self.cluster_groups[0]
        except IndexError:
            pass

    @property
    def num_processors(self):
        if not self._num_procs:
            self._num_procs = int(
                self.ssh.execute(
                    'cat /proc/cpuinfo | grep processor | wc -l')[0])
        return self._num_procs

    @property
    def memory(self):
        if not self._memory:
            self._memory = float(
                self.ssh.execute(
                    "free -m | grep -i mem | awk '{print $2}'")[0])
        return self._memory

    @property
    def ip_address(self):
        return self.instance.ip_address

    @property
    def public_dns_name(self):
        return self.instance.public_dns_name

    @property
    def private_ip_address(self):
        return self.instance.private_ip_address

    @property
    def private_dns_name(self):
        return self.instance.private_dns_name

    @property
    def private_dns_name_short(self):
        return self.instance.private_dns_name.split('.')[0]

    @property
    def id(self):
        return self.instance.id

    @property
    def block_device_mapping(self):
        return self.instance.block_device_mapping

    @property
    def dns_name(self):
        return self.instance.dns_name

    @property
    def state(self):
        return self.instance.state

    @property
    def launch_time(self):
        return self.instance.launch_time

    @property
    def local_launch_time(self):
        ltime = utils.iso_to_localtime_tuple(self.launch_time)
        return time.strftime("%Y-%m-%d %H:%M:%S", ltime.timetuple())

    @property
    def uptime(self):
        return utils.get_elapsed_time(self.launch_time)

    @property
    def ami_launch_index(self):
        try:
            return int(self.instance.ami_launch_index)
        except TypeError:
            log.error("instance %s (state: %s) has no ami_launch_index" %
                      (self.id, self.state))
            log.error("returning 0 as ami_launch_index...")
            return 0

    @property
    def key_name(self):
        return self.instance.key_name

    @property
    def arch(self):
        return self.instance.architecture

    @property
    def kernel(self):
        return self.instance.kernel

    @property
    def ramdisk(self):
        return self.instance.ramdisk

    @property
    def instance_type(self):
        return self.instance.instance_type

    @property
    def image_id(self):
        return self.instance.image_id

    @property
    def placement(self):
        return self.instance.placement

    @property
    def region(self):
        return self.instance.region

    @property
    def root_device_name(self):
        root_dev = self.instance.root_device_name
        bmap = self.block_device_mapping
        if bmap and root_dev not in bmap and self.is_ebs_backed():
            # Hack for misconfigured AMIs (e.g. CentOS 6.3 Marketplace) These
            # AMIs have root device name set to /dev/sda1 but no /dev/sda1 in
            # block device map - only /dev/sda. These AMIs somehow magically
            # work so check if /dev/sda exists and return that instead to
            # prevent detach_external_volumes() from trying to detach the root
            # volume on these AMIs.
            log.warn("Root device %s is not in the block device map" %
                     root_dev)
            log.warn("This means the AMI was registered with either "
                     "an incorrect root device name or an incorrect block "
                     "device mapping")
            sda, sda1 = '/dev/sda', '/dev/sda1'
            if root_dev == sda1:
                log.info("Searching for possible root device: %s" % sda)
                if sda in self.block_device_mapping:
                    log.warn("Found '%s' - assuming its the real root device" %
                             sda)
                    root_dev = sda
                else:
                    log.warn("Device %s isn't in the block device map either" %
                             sda)
        return root_dev

    @property
    def root_device_type(self):
        return self.instance.root_device_type

    def add_user_to_group(self, user, group):
        """
        Add user (if exists) to group (if exists)
        """
        if not user in self.get_user_map():
            raise exception.BaseException("user %s does not exist" % user)
        if group in self.get_group_map():
            self.ssh.execute('gpasswd -a %s %s' % (user, 'utmp'))
        else:
            raise exception.BaseException("group %s does not exist" % group)

    def get_group_map(self, key_by_gid=False):
        """
        Returns dictionary where keys are remote group names and values are
        grp.struct_grp objects from the standard grp module

        key_by_gid=True will use the integer gid as the returned dictionary's
        keys instead of the group's name
        """
        grp_file = self.ssh.remote_file('/etc/group', 'r')
        groups = [l.strip().split(':') for l in grp_file.readlines()]
        grp_file.close()
        grp_map = {}
        for group in groups:
            name, passwd, gid, mems = group
            gid = int(gid)
            mems = mems.split(',')
            key = name
            if key_by_gid:
                key = gid
            grp_map[key] = utils.struct_group([name, passwd, gid, mems])
        return grp_map

    def get_user_map(self, key_by_uid=False):
        """
        Returns dictionary where keys are remote usernames and values are
        pwd.struct_passwd objects from the standard pwd module

        key_by_uid=True will use the integer uid as the returned dictionary's
        keys instead of the user's login name
        """
        etc_passwd = self.ssh.remote_file('/etc/passwd', 'r')
        users = [l.strip().split(':') for l in etc_passwd.readlines()]
        etc_passwd.close()
        user_map = {}
        for user in users:
            name, passwd, uid, gid, gecos, home, shell = user
            uid = int(uid)
            gid = int(gid)
            key = name
            if key_by_uid:
                key = uid
            user_map[key] = utils.struct_passwd([name, passwd, uid, gid, gecos,
                                                 home, shell])
        return user_map

    def getgrgid(self, gid):
        """
        Remote version of the getgrgid method in the standard grp module

        returns a grp.struct_group
        """
        gmap = self.get_group_map(key_by_gid=True)
        return gmap.get(gid)

    def getgrnam(self, groupname):
        """
        Remote version of the getgrnam method in the standard grp module

        returns a grp.struct_group
        """
        gmap = self.get_group_map()
        return gmap.get(groupname)

    def getpwuid(self, uid):
        """
        Remote version of the getpwuid method in the standard pwd module

        returns a pwd.struct_passwd
        """
        umap = self.get_user_map(key_by_uid=True)
        return umap.get(uid)

    def getpwnam(self, username):
        """
        Remote version of the getpwnam method in the standard pwd module

        returns a pwd.struct_passwd
        """
        umap = self.get_user_map()
        return umap.get(username)

    def add_user(self, name, uid=None, gid=None, shell="bash"):
        """
        Add a user to the remote system.

        name - the username of the user being added
        uid - optional user id to use when creating new user
        gid - optional group id to use when creating new user
        shell - optional shell assign to new user (default: bash)
        """
        if gid:
            self.ssh.execute('groupadd -o -g %s %s' % (gid, name))
        user_add_cmd = 'useradd -o '
        if uid:
            user_add_cmd += '-u %s ' % uid
        if gid:
            user_add_cmd += '-g %s ' % gid
        if shell:
            user_add_cmd += '-s `which %s` ' % shell
        user_add_cmd += "-m %s" % name
        self.ssh.execute(user_add_cmd)

    def generate_key_for_user(self, username, ignore_existing=False,
                              auth_new_key=False, auth_conn_key=False):
        """
        Generates an id_rsa/id_rsa.pub keypair combo for a user on the remote
        machine.

        ignore_existing - if False, any existing key combos will be used rather
        than generating a new RSA key

        auth_new_key - if True, add the newly generated public key to the
        remote user's authorized_keys file

        auth_conn_key - if True, add the public key used to establish this ssh
        connection to the remote user's authorized_keys
        """
        user = self.getpwnam(username)
        home_folder = user.pw_dir
        ssh_folder = posixpath.join(home_folder, '.ssh')
        if not self.ssh.isdir(ssh_folder):
            self.ssh.mkdir(ssh_folder)
        self.ssh.chown(user.pw_uid, user.pw_gid, ssh_folder)
        private_key = posixpath.join(ssh_folder, 'id_rsa')
        public_key = private_key + '.pub'
        authorized_keys = posixpath.join(ssh_folder, 'authorized_keys')
        key_exists = self.ssh.isfile(private_key)
        if key_exists and not ignore_existing:
            log.debug("Using existing key: %s" % private_key)
            key = self.ssh.load_remote_rsa_key(private_key)
        else:
            key = self.ssh.generate_rsa_key()
        pubkey_contents = self.ssh.get_public_key(key)
        if not key_exists or ignore_existing:
            # copy public key to remote machine
            pub_key = self.ssh.remote_file(public_key, 'w')
            pub_key.write(pubkey_contents)
            pub_key.chown(user.pw_uid, user.pw_gid)
            pub_key.chmod(0400)
            pub_key.close()
            # copy private key to remote machine
            priv_key = self.ssh.remote_file(private_key, 'w')
            key.write_private_key(priv_key)
            priv_key.chown(user.pw_uid, user.pw_gid)
            priv_key.chmod(0400)
            priv_key.close()
        if not auth_new_key or not auth_conn_key:
            return key
        auth_keys_contents = ''
        if self.ssh.isfile(authorized_keys):
            auth_keys = self.ssh.remote_file(authorized_keys, 'r')
            auth_keys_contents = auth_keys.read()
            auth_keys.close()
        auth_keys = self.ssh.remote_file(authorized_keys, 'a')
        if auth_new_key:
            # add newly generated public key to user's authorized_keys
            if pubkey_contents not in auth_keys_contents:
                log.debug("adding auth_key_contents")
                auth_keys.write('%s\n' % pubkey_contents)
        if auth_conn_key and self.ssh._pkey:
            # add public key used to create the connection to user's
            # authorized_keys
            conn_key = self.ssh._pkey
            conn_pubkey_contents = self.ssh.get_public_key(conn_key)
            if conn_pubkey_contents not in auth_keys_contents:
                log.debug("adding conn_pubkey_contents")
                auth_keys.write('%s\n' % conn_pubkey_contents)
        auth_keys.chown(user.pw_uid, user.pw_gid)
        auth_keys.chmod(0600)
        auth_keys.close()
        return key

    def add_to_known_hosts(self, username, nodes, add_self=True):
        """
        Populate user's known_hosts file with pub keys from hosts in nodes list

        username - name of the user to add to known hosts for
        nodes - the nodes to add to the user's known hosts file
        add_self - add this Node to known_hosts in addition to nodes
        """
        user = self.getpwnam(username)
        known_hosts_file = posixpath.join(user.pw_dir, '.ssh', 'known_hosts')
        khosts = []
        if add_self and self not in nodes:
            nodes.append(self)
        self.remove_from_known_hosts(username, nodes)
        for node in nodes:
            server_pkey = node.ssh.get_server_public_key()
            node_names = {}.fromkeys([node.alias, node.private_dns_name,
                                      node.private_dns_name_short],
                                     node.private_ip_address)
            node_names[node.public_dns_name] = node.ip_address
            for name, ip in node_names.items():
                name_ip = "%s,%s" % (name, ip)
                khosts.append(' '.join([name_ip, server_pkey.get_name(),
                                        base64.b64encode(str(server_pkey))]))
        khostsf = self.ssh.remote_file(known_hosts_file, 'a')
        khostsf.write('\n'.join(khosts) + '\n')
        khostsf.chown(user.pw_uid, user.pw_gid)
        khostsf.close()

    def remove_from_known_hosts(self, username, nodes):
        """
        Remove all network names for nodes from username's known_hosts file
        on this Node
        """
        user = self.getpwnam(username)
        known_hosts_file = posixpath.join(user.pw_dir, '.ssh', 'known_hosts')
        hostnames = []
        for node in nodes:
            hostnames += [node.alias, node.private_dns_name,
                          node.private_dns_name_short, node.public_dns_name]
        if self.ssh.isfile(known_hosts_file):
            regex = '|'.join(hostnames)
            self.ssh.remove_lines_from_file(known_hosts_file, regex)

    def enable_passwordless_ssh(self, username, nodes):
        """
        Configure passwordless ssh for user between this Node and nodes
        """
        user = self.getpwnam(username)
        ssh_folder = posixpath.join(user.pw_dir, '.ssh')
        priv_key_file = posixpath.join(ssh_folder, 'id_rsa')
        pub_key_file = priv_key_file + '.pub'
        known_hosts_file = posixpath.join(ssh_folder, 'known_hosts')
        auth_key_file = posixpath.join(ssh_folder, 'authorized_keys')
        self.add_to_known_hosts(username, nodes)
        # exclude this node from copying
        nodes = filter(lambda n: n.id != self.id, nodes)
        # copy private key and public key to node
        self.copy_remote_file_to_nodes(priv_key_file, nodes)
        self.copy_remote_file_to_nodes(pub_key_file, nodes)
        # copy authorized_keys and known_hosts to node
        self.copy_remote_file_to_nodes(auth_key_file, nodes)
        self.copy_remote_file_to_nodes(known_hosts_file, nodes)

    def copy_remote_file_to_node(self, remote_file, node, dest=None):
        return self.copy_remote_file_to_nodes(remote_file, [node], dest=dest)

    def copy_remote_file_to_nodes(self, remote_file, nodes, dest=None):
        """
        Copies a remote file from this Node instance to another Node instance
        without passwordless ssh between the two.

        dest - path to store the data in on the node (defaults to remote_file)
        """
        if not dest:
            dest = remote_file
        rf = self.ssh.remote_file(remote_file, 'r')
        contents = rf.read()
        sts = rf.stat()
        mode = stat.S_IMODE(sts.st_mode)
        uid = sts.st_uid
        gid = sts.st_gid
        rf.close()
        for node in nodes:
            if self.id == node.id and remote_file == dest:
                log.warn("src and destination are the same: %s, skipping" %
                         remote_file)
                continue
            nrf = node.ssh.remote_file(dest, 'w')
            nrf.write(contents)
            nrf.chown(uid, gid)
            nrf.chmod(mode)
            nrf.close()

    def remove_user(self, name):
        """
        Remove a user from the remote system
        """
        self.ssh.execute('userdel %s' % name)
        self.ssh.execute('groupdel %s' % name)

    def export_fs_to_nodes(self, nodes, export_paths):
        """
        Export each path in export_paths to each node in nodes via NFS

        nodes - list of nodes to export each path to
        export_paths - list of paths on this remote host to export to each node

        Example:
        # export /home and /opt/sge6 to each node in nodes
        $ node.start_nfs_server()
        $ node.export_fs_to_nodes(nodes=[node1,node2],
                                  export_paths=['/home', '/opt/sge6'])
        """
        # setup /etc/exports
        log.info("Configuring NFS exports path(s):\n%s" %
                 ' '.join(export_paths))
        nfs_export_settings = "(async,no_root_squash,no_subtree_check,rw)"
        etc_exports = self.ssh.remote_file('/etc/exports', 'r')
        contents = etc_exports.read()
        etc_exports.close()
        etc_exports = self.ssh.remote_file('/etc/exports', 'a')
        for node in nodes:
            for path in export_paths:
                export_line = ' '.join(
                    [path, node.alias + nfs_export_settings + '\n'])
                if export_line not in contents:
                    etc_exports.write(export_line)
        etc_exports.close()
        self.ssh.execute('exportfs -fra')

    def stop_exporting_fs_to_nodes(self, nodes):
        """
        Removes nodes from this node's /etc/exportfs

        nodes - list of nodes to stop

        Example:
        $ node.remove_export_fs_to_nodes(nodes=[node1,node2])
        """
        regex = '|'.join(map(lambda x: x.alias, nodes))
        self.ssh.remove_lines_from_file('/etc/exports', regex)
        self.ssh.execute('exportfs -fra')

    def start_nfs_server(self):
        log.info("Starting NFS server on %s" % self.alias)
        self.ssh.execute('/etc/init.d/portmap start')
        self.ssh.execute('mount -t rpc_pipefs sunrpc /var/lib/nfs/rpc_pipefs/',
                         ignore_exit_status=True)
        self.ssh.execute('/etc/init.d/nfs start')
        self.ssh.execute('/usr/sbin/exportfs -fra')

    def mount_nfs_shares(self, server_node, remote_paths):
        """
        Mount each path in remote_paths from the remote server_node

        server_node - remote server node that is sharing the remote_paths
        remote_paths - list of remote paths to mount from server_node
        """
        self.ssh.execute('/etc/init.d/portmap start')
        # TODO: move this fix for xterm somewhere else
        self.ssh.execute('mount -t devpts none /dev/pts',
                         ignore_exit_status=True)
        mount_map = self.get_mount_map()
        mount_paths = []
        for path in remote_paths:
            network_device = "%s:%s" % (server_node.alias, path)
            if network_device in mount_map:
                mount_path, typ, options = mount_map.get(network_device)
                log.debug('nfs share %s already mounted to %s on '
                          'node %s, skipping...' %
                          (network_device, mount_path, self.alias))
            else:
                mount_paths.append(path)
        remote_paths = mount_paths
        remote_paths_regex = '|'.join(map(lambda x: x.center(len(x) + 2),
                                          remote_paths))
        self.ssh.remove_lines_from_file('/etc/fstab', remote_paths_regex)
        fstab = self.ssh.remote_file('/etc/fstab', 'a')
        for path in remote_paths:
            fstab.write('%s:%s %s nfs vers=3,user,rw,exec,noauto 0 0\n' %
                        (server_node.alias, path, path))
        fstab.close()
        for path in remote_paths:
            if not self.ssh.path_exists(path):
                self.ssh.makedirs(path)
            self.ssh.execute('mount %s' % path)

    def get_mount_map(self):
        mount_map = {}
        mount_lines = self.ssh.execute('mount')
        for line in mount_lines:
            dev, on_label, path, type_label, fstype, options = line.split()
            mount_map[dev] = [path, fstype, options]
        return mount_map

    def get_device_map(self):
        """
        Returns a dictionary mapping devices->(# of blocks) based on
        'fdisk -l' and /proc/partitions
        """
        dev_regex = '/dev/[A-Za-z0-9/]+'
        r = re.compile('Disk (%s):' % dev_regex)
        fdiskout = '\n'.join(self.ssh.execute("fdisk -l 2>/dev/null"))
        proc_parts = '\n'.join(self.ssh.execute("cat /proc/partitions"))
        devmap = {}
        for dev in r.findall(fdiskout):
            short_name = dev.replace('/dev/', '')
            r = re.compile("(\d+)\s+%s(?:\s+|$)" % short_name)
            devmap[dev] = int(r.findall(proc_parts)[0])
        return devmap

    def get_partition_map(self, device=None):
        """
        Returns a dictionary mapping partitions->(start, end, blocks, id) based
        on 'fdisk -l'
        """
        fdiskout = '\n'.join(self.ssh.execute("fdisk -l %s 2>/dev/null" %
                                              (device or '')))
        part_regex = '/dev/[A-Za-z0-9/]+'
        r = re.compile('(%s)\s+\*?\s+'
                       '(\d+)(?:[-+])?\s+'
                       '(\d+)(?:[-+])?\s+'
                       '(\d+)(?:[-+])?\s+'
                       '([\da-fA-F][\da-fA-F]?)' % part_regex)
        partmap = {}
        for match in r.findall(fdiskout):
            part, start, end, blocks, sys_id = match
            partmap[part] = [int(start), int(end), int(blocks), sys_id]
        return partmap

    def mount_device(self, device, path):
        """
        Mount device to path
        """
        self.ssh.remove_lines_from_file('/etc/fstab',
                                        path.center(len(path) + 2))
        master_fstab = self.ssh.remote_file('/etc/fstab', mode='a')
        master_fstab.write("%s %s auto noauto,defaults 0 0\n" %
                           (device, path))
        master_fstab.close()
        if not self.ssh.path_exists(path):
            self.ssh.makedirs(path)
        self.ssh.execute('mount %s' % path)

    def add_to_etc_hosts(self, nodes):
        """
        Adds all names for node in nodes arg to this node's /etc/hosts file
        """
        self.remove_from_etc_hosts(nodes)
        host_file = self.ssh.remote_file('/etc/hosts', 'a')
        for node in nodes:
            print >> host_file, node.get_hosts_entry()
        host_file.close()

    def remove_from_etc_hosts(self, nodes):
        """
        Remove all network names for node in nodes arg from this node's
        /etc/hosts file
        """
        aliases = map(lambda x: x.alias, nodes)
        self.ssh.remove_lines_from_file('/etc/hosts', '|'.join(aliases))

    def set_hostname(self, hostname=None):
        """
        Set this node's hostname to self.alias

        hostname - optional hostname to set (defaults to self.alias)
        """
        hostname = hostname or self.alias
        hostname_file = self.ssh.remote_file("/etc/hostname", "w")
        hostname_file.write(hostname)
        hostname_file.close()
        self.ssh.execute('hostname -F /etc/hostname')

    @property
    def network_names(self):
        """ Returns all network names for this node in a dictionary"""
        names = {}
        names['INTERNAL_IP'] = self.private_ip_address
        names['INTERNAL_NAME'] = self.private_dns_name
        names['INTERNAL_NAME_SHORT'] = self.private_dns_name_short
        names['INTERNAL_ALIAS'] = self.alias
        return names

    @property
    def attached_vols(self):
        """
        Returns a dictionary of all attached volumes minus the root device in
        the case of EBS backed instances
        """
        attached_vols = {}
        attached_vols.update(self.block_device_mapping)
        if self.is_ebs_backed():
            # exclude the root device from the list
            root_dev = self.root_device_name
            if root_dev in attached_vols:
                attached_vols.pop(root_dev)
        return attached_vols

    def detach_external_volumes(self):
        """
        Detaches all volumes returned by self.attached_vols
        """
        block_devs = self.attached_vols
        for dev in block_devs:
            vol_id = block_devs[dev].volume_id
            vol = self.ec2.get_volume(vol_id)
            log.info("Detaching volume %s from %s" % (vol.id, self.alias))
            if vol.status not in ['available', 'detaching']:
                vol.detach()

    def delete_root_volume(self):
        """
        Detach and destroy EBS root volume (EBS-backed node only)
        """
        if not self.is_ebs_backed():
            return
        root_vol = self.block_device_mapping[self.root_device_name]
        vol_id = root_vol.volume_id
        vol = self.ec2.get_volume(vol_id)
        vol.detach()
        while vol.update() != 'available':
            time.sleep(5)
        log.info("Deleting node %s's root volume" % self.alias)
        root_vol.delete()

    @property
    def spot_id(self):
        if self.instance.spot_instance_request_id:
            return self.instance.spot_instance_request_id

    def get_spot_request(self):
        spot = self.ec2.get_all_spot_requests(
            filters={'spot-instance-request-id': self.spot_id})
        if spot:
            return spot[0]

    def is_master(self):
        return self.alias == "master"

    def is_instance_store(self):
        return self.instance.root_device_type == "instance-store"

    def is_ebs_backed(self):
        return self.instance.root_device_type == "ebs"

    def is_cluster_compute(self):
        return self.instance.instance_type in static.CLUSTER_COMPUTE_TYPES

    def is_gpu_compute(self):
        return self.instance.instance_type in static.CLUSTER_GPU_TYPES

    def is_cluster_type(self):
        return self.instance.instance_type in static.CLUSTER_TYPES

    def is_spot(self):
        return self.spot_id is not None

    def is_stoppable(self):
        return self.is_ebs_backed() and not self.is_spot()

    def is_stopped(self):
        return self.state == "stopped"

    def start(self):
        """
        Starts EBS-backed instance and puts it in the 'running' state.
        Only works if this node is EBS-backed, raises
        exception.InvalidOperation otherwise.
        """
        if not self.is_ebs_backed():
            raise exception.InvalidOperation(
                "Only EBS-backed instances can be started")
        return self.instance.start()

    def stop(self):
        """
        Shutdown EBS-backed instance and put it in the 'stopped' state.
        Only works if this node is EBS-backed, raises
        exception.InvalidOperation otherwise.

        NOTE: The EBS root device will *not* be deleted and the instance can
        be 'started' later on.
        """
        if self.is_spot():
            raise exception.InvalidOperation(
                "spot instances can not be stopped")
        elif not self.is_ebs_backed():
            raise exception.InvalidOperation(
                "Only EBS-backed instances can be stopped")
        if not self.is_stopped():
            log.info("Stopping node: %s (%s)" % (self.alias, self.id))
            return self.instance.stop()
        else:
            log.info("Node '%s' is already stopped" % self.alias)

    def terminate(self):
        """
        Shutdown and destroy this instance. For EBS-backed nodes, this
        will also destroy the node's EBS root device. Puts this node
        into a 'terminated' state.
        """
        if self.spot_id:
            log.info("Canceling spot request %s" % self.spot_id)
            self.get_spot_request().cancel()
        log.info("Terminating node: %s (%s)" % (self.alias, self.id))
        return self.instance.terminate()

    def shutdown(self):
        """
        Shutdown this instance. This method will terminate traditional
        instance-store instances and stop EBS-backed instances
        (i.e. not destroy EBS root dev)
        """
        if self.is_stoppable():
            self.stop()
        else:
            self.terminate()

    def reboot(self):
        """
        Reboot this instance.
        """
        self.instance.reboot()

    def is_ssh_up(self):
        try:
            return self.ssh.transport is not None
        except exception.SSHError:
            return False

    def wait(self, interval=30):
        while not self.is_up():
            time.sleep(interval)

    def is_up(self):
        if self.update() != 'running':
            return False
        if not self.is_ssh_up():
            return False
        if self.private_ip_address is None:
            log.debug("instance %s has no private_ip_address" % self.id)
            log.debug("attempting to determine private_ip_address for "
                      "instance %s" % self.id)
            try:
                private_ip = self.ssh.execute(
                    'python -c '
                    '"import socket; print socket.gethostbyname(\'%s\')"' %
                    self.private_dns_name)[0].strip()
                log.debug("determined instance %s's private ip to be %s" %
                          (self.id, private_ip))
                self.instance.private_ip_address = private_ip
            except Exception, e:
                print e
                return False
        return True

    def update(self):
        res = self.ec2.get_all_instances(filters={'instance-id': self.id})
        self.instance = res[0]
        return self.state

    @property
    def ssh(self):
        if not self._ssh:
            self._ssh = sshutils.SSHClient(self.instance.dns_name,
                                           username=self.user,
                                           private_key=self.key_location)
        return self._ssh

    def shell(self, user=None, forward_x11=False, forward_agent=False,
              command=None):
        """
        Attempts to launch an interactive shell by first trying the system's
        ssh client. If the system does not have the ssh command it falls back
        to a pure-python ssh shell.
        """
        if self.update() != 'running':
            try:
                alias = self.alias
            except exception.BaseException:
                alias = None
            label = 'instance'
            if alias == "master":
                label = "master"
                alias = "node"
            elif alias:
                label = "node"
            instance_id = alias or self.id
            raise exception.InstanceNotRunning(instance_id, self.state,
                                               label=label)
        user = user or self.user
        if utils.has_required(['ssh']):
            log.debug("Using native OpenSSH client")
            sshopts = '-i %s' % self.key_location
            if forward_x11:
                sshopts += ' -Y'
            if forward_agent:
                sshopts += ' -A'
            ssh_cmd = static.SSH_TEMPLATE % dict(opts=sshopts, user=user,
                                                 host=self.dns_name)
            if command:
                command = "'source /etc/profile && %s'" % command
                ssh_cmd = ' '.join([ssh_cmd, command])
            log.debug("ssh_cmd: %s" % ssh_cmd)
            return subprocess.call(ssh_cmd, shell=True)
        else:
            log.debug("Using Pure-Python SSH client")
            if forward_x11:
                log.warn("X11 Forwarding not available in Python SSH client")
            if forward_agent:
                log.warn("Authentication agent forwarding not available in " +
                         "Python SSH client")
            if command:
                orig_user = self.ssh.get_current_user()
                self.ssh.switch_user(user)
                self.ssh.execute(command, silent=False)
                self.ssh.switch_user(orig_user)
                return self.ssh.get_last_status()
            self.ssh.interactive_shell(user=user)

    def get_hosts_entry(self):
        """ Returns /etc/hosts entry for this node """
        etc_hosts_line = "%(INTERNAL_IP)s %(INTERNAL_ALIAS)s"
        etc_hosts_line = etc_hosts_line % self.network_names
        return etc_hosts_line

    def apt_command(self, cmd):
        """
        Run an apt-get command with all the necessary options for
        non-interactive use (DEBIAN_FRONTEND=interactive, -y, --force-yes, etc)
        """
        dpkg_opts = "Dpkg::Options::='--force-confnew'"
        cmd = "apt-get -o %s -y --force-yes %s" % (dpkg_opts, cmd)
        cmd = "DEBIAN_FRONTEND='noninteractive' " + cmd
        self.ssh.execute(cmd)

    def apt_install(self, pkgs):
        """
        Install a set of packages via apt-get.

        pkgs is a string that contains one or more packages separated by a
        space
        """
        self.apt_command('install %s' % pkgs)

    def yum_command(self, cmd):
        """
        Run a yum command with all necessary options for non-interactive use.
        "-d 0 -e 0 -y"
        """
        yum_opts = ['-d', '0', '-e', '0', '-y']
        cmd = "yum " + " ".join(yum_opts) + " " + cmd
        self.ssh.execute(cmd)

    def yum_install(self, pkgs):
        """
        Install a set of packages via yum.

        pkgs is a string that contains one or more packages separated by a
        space
        """
        self.yum_command('install %s' % pkgs)

    @property
    def package_provider(self):
        """
        In order to determine which packaging system to use, check to see if
        /usr/bin/apt exists on the node, and use apt if it exists. Otherwise
        test to see if /usr/bin/yum exists and use that.
        """
        if self.ssh.isfile('/usr/bin/apt'):
            return "apt"
        elif self.ssh.isfile('/usr/bin/yum'):
            return "yum"

    def package_install(self, pkgs):
        """
        Provides a declarative install packages on systems, regardless
        of the system's packging type (apt/yum).
        """
        if self.package_provider == "apt":
            self.apt_install(pkgs)
        elif self.package_provider == "yum":
            self.yum_install(pkgs)

    def __del__(self):
        if self._ssh:
            self._ssh.close()
