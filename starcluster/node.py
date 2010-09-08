#!/usr/bin/env python
import os
import socket
from starcluster import exception
from starcluster import ssh
from starcluster.logger import log

def ssh_to_node(node_id, cfg, user='root'):
    ec2 = cfg.get_easy_ec2()
    instances = ec2.get_all_instances()
    node = None
    for instance in instances:
        if instance.dns_name == node_id:
            node = instance
            break
        elif instance.id == node_id:
            node = instance
            break
    if node:
        key = cfg.get_key(node.key_name)
        os.system('ssh -i %s %s@%s' % (key.key_location, user, 
                                       node.dns_name))
    else:
        log.error("node %s does not exist" % node_id)

def get_node(node_id, cfg):
    """Factory for Node class"""
    ec2 = cfg.get_easy_ec2()
    instances = ec2.get_all_instances()
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
    key_location = cfg.keys.get(node.key_name, {}).get('key_location')
    alias = node_id
    node = Node(node, key_location, node_id)
    return node

class Node(object):
    """
    This class represents a single compute node in a StarCluster. 
    
    It contains all useful metadata for the node such as the internal/external 
    hostnames, ips, etc as well as a paramiko ssh object for executing commands,
    creating/modifying files on the node.

    Takes boto.ec2.instance.Instance, key_location, and alias as input and
    optionally a user to ssh as (defaults to root)
    """
    def __init__(self, instance, key_location, alias, user='root'):
        self.instance = instance
        self.key_location = key_location
        self.alias = alias
        self.user = user
        self._ssh = None
        self._num_procs = None
        self._memory = None

    def __repr__(self):
        return '<Node: %s (%s)>' % (self.alias, self.id)

    @property
    def num_processors(self):
        if not self._num_procs:
            self._num_procs = int(
                self.ssh.execute('cat /proc/cpuinfo | grep processor | wc -l')[0])
        return self._num_procs

    @property
    def memory(self):
        if not self._memory:
            self._memory = float(
                self.ssh.execute("free -m | grep -i mem | awk '{print $2}'")[0])
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
    def key_name(self):
        return self.instance.key_name

    @property
    def arch(self):
        return self.instance.architecture

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
    def root_device_type(self):
        return self.instance.root_device_type

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
        Only works if this node is EBS-backed, raises exception.InvalidOperation
        otherwise.
        """
        if not self.is_ebs_backed():
            raise exception.InvalidOperation(
                "Only EBS-backed instances can be started")
        return self.instance.start()

    def stop(self):
        """
        Shutdown EBS-backed instance and put it in the 'stopped' state.
        Only works if this node is EBS-backed, raises exception.InvalidOperation
        otherwise.

        NOTE: The EBS root device will *not* be deleted and the instance can
        be 'started' later on.
        """
        if not self.is_ebs_backed():
            raise exception.InvalidOperation(
                "Only EBS-backed instances can be stopped")
        return self.instance.stop()

    def terminate(self):
        """
        Shutdown and destroy this instance. For EBS-backed instances, this will
        also destroy the EBS root device for the instance. Puts this instance 
        into a 'terminated' state
        """
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
            log.debug(
                "attempting to determine private_ip_address for instance %s" % \
                self.id)
            try:
                private_ip = self.ssh.execute(
                    'python -c "import socket; print socket.gethostbyname(\'%s\')"' % \
                    self.private_dns_name)[0].strip()
                log.debug("determined instance %s's private ip to be %s" % \
                          (self.id, private_ip))
                self.instance.private_ip_address = private_ip
            except Exception,e:
                print e
                return False
        return True

    def update(self):
        retval = self.instance.update()
        return retval

    @property
    def ssh(self):
        if not self._ssh:
            self._ssh = ssh.Connection(self.instance.dns_name,
                                       username=self.user,
                                       private_key=self.key_location)
        return self._ssh

    def get_hosts_entry(self):
        """ Returns /etc/hosts entry for this node """
        etc_hosts_line = "%(INTERNAL_IP)s %(INTERNAL_NAME)s %(INTERNAL_NAME_SHORT)s %(INTERNAL_ALIAS)s" 
        etc_hosts_line = etc_hosts_line % self.network_names
        return etc_hosts_line

    def __del__(self):
        if self._ssh:
            self._ssh.close()
