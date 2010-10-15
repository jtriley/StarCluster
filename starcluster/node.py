#!/usr/bin/env python
import os
import time
import socket

from starcluster import ssh
from starcluster import utils
from starcluster import static
from starcluster import awsutils
from starcluster import managers
from starcluster import exception
from starcluster.logger import log


class NodeManager(managers.Manager):
    """
    Manager class for Node objects
    """
    def ssh_to_node(self, node_id, user='root'):
        node = self.get_node(node_id, user=user)
        node.shell(user=user)

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
    hostnames, ips, etc as well as a paramiko ssh object for executing
    commands, creating/modifying files on the node.

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
        self.ec2 = awsutils.EasyEC2(None, None)
        self.ec2._conn = instance.connection
        self.key_location = key_location
        self.user = user
        self._alias = alias
        self._ssh = None
        self._num_procs = None
        self._memory = None

    def __repr__(self):
        return '<Node: %s (%s)>' % (self.alias, self.id)

    @property
    def alias(self):
        """
        Return the alias stored in this node's user data.
        Alias returned as:
            user_data.split('|')[self.ami_launch_index]
        """
        if not self._alias:
            user_data = self.ec2.get_instance_user_data(self.id)
            aliases = user_data.split('|')
            index = self.ami_launch_index
            alias = aliases[index]
            if not alias:
                # TODO: raise exception about old version
                raise exception.BaseException(
                    "instance %s has no alias" % alias)
            return alias
        return self._alias

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
    def ami_launch_index(self):
        return int(self.instance.ami_launch_index)

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
    def root_device_name(self):
        return self.instance.root_device_name

    @property
    def root_device_type(self):
        return self.instance.root_device_type

    def set_hostname_to_alias(self):
        """
        Set this node's hostname to self.alias
        """
        hostname_file = self.ssh.remote_file("/etc/hostname", "w")
        hostname_file.write(self.alias)
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
            attached_vols.pop(self.root_device_name)
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
        while vol.update() != 'availabile':
            time.sleep(5)
        log.info("Deleting node %s's root volume" % self.alias)
        root_vol.delete()

    @property
    def spot_id(self):
        return self.instance.spot_instance_request_id

    def is_master(self):
        return self.alias == "master"

    def is_instance_store(self):
        return self.instance.root_device_type == "instance-store"

    def is_ebs_backed(self):
        return self.instance.root_device_type == "ebs"

    def is_spot(self):
        return self.spot_id is not None

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
        log.info("Stopping instance: %s (%s)" % (self.alias, self.id))
        return self.instance.stop()

    def terminate(self):
        """
        Shutdown and destroy this instance. For EBS-backed nodes, this
        will also destroy the node's EBS root device. Puts this node
        into a 'terminated' state.
        """
        log.info("Terminating node: %s (%s)" % (self.alias, self.id))
        return self.instance.terminate()

    def shutdown(self):
        """
        Shutdown this instance. This method will terminate traditional
        instance-store instances and stop EBS-backed instances
        (ie not destroy EBS root dev)
        """
        if self.is_ebs_backed() and not self.is_spot():
            self.stop()
        else:
            self.terminate()

    def is_ssh_up(self):
        timeout = 10.0
        s = socket.socket()
        s.settimeout(timeout)
        try:
            s.connect((self.dns_name, 22))
            s.close()
            return True
        except socket.timeout:
            log.debug(
                "connecting to port 22 on timed out after % seconds" % timeout)
        except socket.error:
            log.debug("ssh not up for %s" % self.dns_name)
            return False

    def is_up(self):
        self.update()
        if not self.is_ssh_up():
            return False
        if self.private_ip_address is None:
            log.debug("instance %s has no private_ip_address" % self.id)
            log.debug(("attempting to determine private_ip_address for" + \
                       "instance %s") % self.id)
            try:
                private_ip = self.ssh.execute((
                    'python -c ' + \
                    '"import socket; print socket.gethostbyname(\'%s\')"') % \
                    self.private_dns_name)[0].strip()
                log.debug("determined instance %s's private ip to be %s" % \
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
            self._ssh = ssh.SSHClient(self.instance.dns_name,
                                      username=self.user,
                                      private_key=self.key_location)
        return self._ssh

    def shell(self, user=None):
        """
        Attempts to launch an interactive shell by first trying the system's
        ssh client. If the system does not have the ssh command it falls back
        to a pure-python ssh shell.
        """
        if self.state != 'running':
            label = 'instance'
            if self.alias == "master":
                label = "master node"
            elif self.alias:
                label = "node '%s'" % self.alias
            raise exception.InstanceNotRunning(self.id, self.state,
                                               label=label)
        if utils.has_required(['ssh']):
            log.debug("using system's ssh client")
            user = user or self.user
            os.system(static.SSH_TEMPLATE % (self.key_location, user,
                                             self.dns_name))
        else:
            log.debug("using pure-python ssh client")
            self.ssh.interactive_shell()

    def get_hosts_entry(self):
        """ Returns /etc/hosts entry for this node """
        etc_hosts_line = "%(INTERNAL_IP)s %(INTERNAL_NAME)s "
        etc_hosts_line += "%(INTERNAL_NAME_SHORT)s %(INTERNAL_ALIAS)s"
        etc_hosts_line = etc_hosts_line % self.network_names
        return etc_hosts_line

    def __del__(self):
        if self._ssh:
            self._ssh.close()
