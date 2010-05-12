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

    def stop(self):
        return self.instance.stop()

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
        if hasattr(self.instance.updated, 'private_ip_address'):
            updated_ip = self.instance.updated.private_ip_address
            if updated_ip and not self.instance.private_ip_address:
                self.instance.private_ip_address = updated_ip
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
