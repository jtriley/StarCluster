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
        if key:
            os.system('ssh -i %s %s@%s' % (key.KEY_LOCATION, user, 
                                           node.dns_name))
        else:
            print 'key %s needed to ssh not found' % node.key_name
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
    if node:
        key_location = cfg.keys.get(node.key_name, {}).get('KEY_LOCATION')
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

    def is_master(self):
        return self.alias == "master"

    @property
    def dns_name(self):
        return self.instance.dns_name

    @property
    def state(self):
        return self.instance.state

    @property
    def key_name(self):
        return self.instance.key_name

    def stop(self):
        return self.instance.stop()

    def update(self):
        return self.instance.update()

    @property
    def ssh(self):
        if not self._ssh:
            self._ssh = ssh.Connection(self.instance.dns_name,
                                       username=self.user,
                                       private_key=self.key_location)
        return self._ssh

    @property
    def network_names(self):
        """ Returns all network names for this node in a dictionary"""
        names = {}
        names['INTERNAL_IP'] = self.private_ip_address
        names['INTERNAL_NAME'] = self.private_dns_name
        names['INTERNAL_NAME_SHORT'] = self.private_dns_name_short
        names['INTERNAL_ALIAS'] = self.alias
        return names

    def get_hosts_entry(self):
        """ Returns /etc/hosts entry for this node """
        etc_hosts_line = "%(INTERNAL_IP)s %(INTERNAL_NAME)s %(INTERNAL_NAME_SHORT)s %(INTERNAL_ALIAS)s" 
        etc_hosts_line = etc_hosts_line % self.network_names
        return etc_hosts_line

    def __del__(self):
        if self._ssh:
            self._ssh.close()
