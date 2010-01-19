#!/usr/bin/env python
import os
import time
import socket
import platform
import pprint 

from starcluster import ssh
from starcluster import awsutils
from starcluster import clustersetup
from starcluster import static
from starcluster.utils import print_timing
from starcluster.spinner import Spinner
from starcluster.logger import log, INFO_NO_NEWLINE
from starcluster.node import Node

import boto

def get_cluster(cluster_name, cfg):
    """Factory for Cluster class"""
    try:
        ec2 = cfg.get_easy_ec2()
        cluster = ec2.get_security_group(_get_cluster_name(cluster_name))
    except Exception,e:
        log.error("cluster %s does not exist" % cluster_name)
        return
    kwargs = {}
    kwargs.update(cfg.aws)
    kwargs.update({'CLUSTER_TAG': cluster_name})
    return Cluster(**kwargs)

def ssh_to_master(cluster_name, cfg):
    cluster = get_cluster(cluster_name, cfg)
    if cluster:
        master = cluster.master_node
        if cfg.keys.has_key(master.key_name):
            key = cfg.keys.get(master.key_name)
            os.system('ssh -i %s %s@%s' % (key.KEY_LOCATION, master.user,
                                           master.dns_name))
        else:
            print 'key %s needed to ssh not found' % master.key_name

def ssh_to_cluster_node(cluster_name, node_id, cfg):
    cluster = get_cluster(cluster_name, cfg)
    node = None
    if cluster:
        try:
            node = cluster.nodes[int(node_id)]
        except:
            if node_id.startswith('i-') and len(node_id) == 10:
                node = cluster.get_node_by_id(node_id)
            else:
                node = cluster.get_node_by_dns_name(node_id)
        if node:
            key = cfg.get_key(node.key_name)
            if key:
                os.system('ssh -i %s %s@%s' % (key.KEY_LOCATION, node.user,
                                               node.dns_name))
            else:
                print 'key %s needed to ssh not found' % node.key_name
        else:
            log.error("node %s does not exist" % node_id)

def _get_cluster_name(cluster_name):
    if not cluster_name.startswith(static.SECURITY_GROUP_PREFIX):
        cluster_name = static.SECURITY_GROUP_TEMPLATE % cluster_name
    return cluster_name

def stop_cluster(cluster_name, cfg):
    ec2 = cfg.get_easy_ec2()
    cluster_name = _get_cluster_name(cluster_name)
    try:
        cluster = ec2.get_security_group(cluster_name)
        for node in cluster.instances():
            log.info('Shutting down %s' % node.id)
            node.stop()
        log.info('Removing cluster security group %s' % cluster.name)
        cluster.delete()
    except Exception,e:
        #print e
        log.error("cluster %s does not exist" % cluster_name)

def list_clusters(cfg):
    ec2 = cfg.get_easy_ec2()
    sgs = ec2.get_security_groups()
    starcluster_groups = []
    for sg in sgs:
        is_starcluster = sg.name.startswith(static.SECURITY_GROUP_PREFIX)
        if is_starcluster and sg.name != static.MASTER_GROUP:
            starcluster_groups.append(sg)
    if starcluster_groups:
        for scg in starcluster_groups:
            print scg.name
            for node in scg.instances():
                print "  %s %s" % (node.id, node.dns_name)
    else:
        log.info("No clusters found...")

class Cluster(object):
    def __init__(self,
            AWS_ACCESS_KEY_ID=None,
            AWS_SECRET_ACCESS_KEY=None,
            AWS_USER_ID=None,
            CLUSTER_PROFILE=None,
            CLUSTER_TAG=None,
            CLUSTER_DESCRIPTION=None,
            CLUSTER_SIZE=None,
            CLUSTER_USER=None,
            CLUSTER_SHELL=None,
            MASTER_IMAGE_ID=None,
            NODE_IMAGE_ID=None,
            INSTANCE_TYPE=None,
            AVAILABILITY_ZONE=None,
            KEYNAME=None,
            KEY_LOCATION=None,
            VOLUME=None,
            VOLUME_DEVICE=None,
            VOLUME_PARTITION=None,
            setup_class=clustersetup.ClusterSetup,
            **kwargs):

        now = time.strftime("%Y%m%d%H%M")
        self.AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
        self.AWS_SECRET_ACCESS_KEY = AWS_SECRET_ACCESS_KEY
        self.AWS_USER_ID = AWS_USER_ID
        self.CLUSTER_PROFILE = CLUSTER_PROFILE
        self.CLUSTER_TAG = CLUSTER_TAG
        self.CLUSTER_DESCRIPTION = CLUSTER_DESCRIPTION
        if self.CLUSTER_TAG is None:
            self.CLUSTER_TAG = now
        if CLUSTER_DESCRIPTION is None:
            self.CLUSTER_DESCRIPTION = "Cluster created at %s" % now 
        self.CLUSTER_SIZE = CLUSTER_SIZE
        self.CLUSTER_USER = CLUSTER_USER
        self.CLUSTER_SHELL = CLUSTER_SHELL
        self.MASTER_IMAGE_ID = MASTER_IMAGE_ID
        self.NODE_IMAGE_ID = NODE_IMAGE_ID
        self.INSTANCE_TYPE = INSTANCE_TYPE
        self.AVAILABILITY_ZONE = AVAILABILITY_ZONE
        self.KEYNAME = KEYNAME
        self.KEY_LOCATION = KEY_LOCATION
        self.VOLUME = VOLUME
        self.VOLUME_DEVICE = VOLUME_DEVICE
        self.VOLUME_PARTITION = VOLUME_PARTITION

        self.ec2 = awsutils.EasyEC2(
            AWS_ACCESS_KEY_ID = self.AWS_ACCESS_KEY_ID, 
            AWS_SECRET_ACCESS_KEY = self.AWS_SECRET_ACCESS_KEY
        )
        self.__instance_types = static.INSTANCE_TYPES
        self.__cluster_settings = static.CLUSTER_SETTINGS
        self.__available_shells = static.AVAILABLE_SHELLS
        self._master_reservation = None
        self._node_reservation = None
        self._nodes = None
        self._master = None
        self._setup_class = setup_class

    def update(self, kwargs):
        for key in kwargs.keys():
            if hasattr(self, key):
                self.__dict__[key] = kwargs[key]

    def get(self, name):
        return self.__dict__.get(name)

    def __str__(self):
        cfg = {
            'AWS_ACCESS_KEY_ID': self.AWS_ACCESS_KEY_ID,
            'AWS_SECRET_ACCESS_KEY': self.AWS_SECRET_ACCESS_KEY,
            'AWS_USER_ID': self.AWS_USER_ID,
            'CLUSTER_PROFILE':  self.CLUSTER_PROFILE,
            'CLUSTER_TAG': self.CLUSTER_TAG,
            'CLUSTER_DESCRIPTION': self.CLUSTER_DESCRIPTION,
            'CLUSTER_SIZE': self.CLUSTER_SIZE,
            'CLUSTER_USER': self.CLUSTER_USER,
            'CLUSTER_SHELL': self.CLUSTER_SHELL,
            'MASTER_IMAGE_ID': self.MASTER_IMAGE_ID,
            'NODE_IMAGE_ID': self.NODE_IMAGE_ID,
            'INSTANCE_TYPE': self.INSTANCE_TYPE,
            'AVAILABILITY_ZONE': self.AVAILABILITY_ZONE,
            'KEYNAME': self.KEYNAME,
            'KEY_LOCATION': self.KEY_LOCATION,
            'VOLUME': self.VOLUME,
            'VOLUME_DEVICE': self.VOLUME_DEVICE,
            'VOLUME_PARTITION': self.VOLUME_PARTITION,
        }
        return pprint.pformat(cfg)

    @property
    def _security_group(self):
        return static.SECURITY_GROUP_TEMPLATE % self.CLUSTER_TAG

    @property
    def master_group(self):
        sg = self.ec2.get_or_create_group(static.MASTER_GROUP,
                                          static.MASTER_GROUP_DESCRIPTION)
        return sg

    @property
    def cluster_group(self):
        sg = self.ec2.get_or_create_group(self._security_group,
                                          self.CLUSTER_DESCRIPTION,
                                          auth_group_traffic=True)
        return sg
            
    @property
    def master_node(self):
        if not self._master:
            # TODO: do this with reservation group info instead
            mgroup_instances = self.master_group.instances()
            cgroup_instances = [ node.id for node in self.cluster_group.instances() ]
            for node in mgroup_instances:
                if node.id in cgroup_instances:
                    self._master = Node(node, self.KEY_LOCATION, 'master')
        return self._master

    @property
    def nodes(self):
        if not self._nodes:
            nodes = self.cluster_group.instances()
            self._nodes = []
            master = self.master_node
            nodeid = 1
            for node in nodes:
                if node.id == master.id:
                    self._nodes.insert(0,master)
                    continue
                self._nodes.append(Node(node, self.KEY_LOCATION, 
                                        'node%.3d' % nodeid))
                nodeid += 1
        else:
            for node in self._nodes:
                node.update()
        return self._nodes

    def get_node_by_dns_name(self, dns_name):
        nodes = self.nodes
        for node in nodes:
            if node.dns_name == dns_name:
                return node

    def get_node_by_id(self, instance_id):
        nodes = self.nodes
        for node in nodes:
            if node.id == instance_id:
                return node

    @property
    def running_nodes(self):
        nodes = []
        for node in self.nodes:
            if node.state == 'running':
                nodes.append(node)
        return nodes

    @property
    def volume(self):
        vol = self.ec2.get_volume(self.VOLUME)
        return vol

    def create_cluster(self):
        log.info("Launching a %d-node cluster..." % self.CLUSTER_SIZE)
        if self.MASTER_IMAGE_ID is None:
            self.MASTER_IMAGE_ID = self.NODE_IMAGE_ID
        log.info("Launching master node...")
        log.info("Master AMI: %s" % self.MASTER_IMAGE_ID)
        conn = self.ec2
        master_sg = self.master_group.name
        cluster_sg = self.cluster_group.name
        master_response = conn.run_instances(image_id=self.MASTER_IMAGE_ID,
            instance_type=self.INSTANCE_TYPE,
            min_count=1, max_count=1,
            key_name=self.KEYNAME,
            security_groups=[master_sg, cluster_sg],
            placement=self.AVAILABILITY_ZONE)
        print master_response
        if self.CLUSTER_SIZE > 1:
            log.info("Launching worker nodes...")
            log.info("Node AMI: %s" % self.NODE_IMAGE_ID)
            instances_response = conn.run_instances(image_id=self.NODE_IMAGE_ID,
                instance_type=self.INSTANCE_TYPE,
                min_count=max((self.CLUSTER_SIZE-1)/2, 1),
                max_count=max(self.CLUSTER_SIZE-1,1),
                key_name=self.KEYNAME,
                security_groups=[cluster_sg],
                placement=self.AVAILABILITY_ZONE)
            print instances_response

    def is_ssh_up(self):
        for node in self.running_nodes:
            s = socket.socket()
            s.settimeout(0.25)
            try:
                s.connect((node.dns_name, 22))
                s.close()
            except socket.error:
                return False
        return True

    def is_cluster_up(self):
        """
        Check whether there are CLUSTER_SIZE nodes running
        and that ssh (port 22) is up on all nodes
        """
        if len(self.running_nodes) == self.CLUSTER_SIZE:
            if self.is_ssh_up():
                return True
            else:
                return False
        else:
            return False

    def attach_volume_to_master(self):
        log.info("Attaching volume to master node...")
        vol = self.volume
        if vol.status != "available":
            log.error('Volume not available...please check and try again')
            return
        resp = vol.attach(self.master_node.id, self.VOLUME_DEVICE)
        log.debug("resp = %s" % resp)
        while True:
            vol.update()
            if vol.attachment_state() == 'attached':
                return True
            time.sleep(5)

    def stop_cluster(self):
        resp = raw_input(">>> Shutdown cluster ? (yes/no) ")
        if resp == 'yes':
            if self.VOLUME:
                log.info("Detaching volume (%s) from master" % self.VOLUME)
                self.volume.detach()
                
            for node in self.running_nodes:
                log.info("Shutting down instance: %s " % node.id)
                node.stop()

            log.info("Removing %s security group" % self._security_group)
            self.cluster_group.delete()
        else:
            log.info("Exiting without shutting down instances....")

    @print_timing
    def start(self, create=True):
        log.info("Starting cluster...")
        if create:
            self.create_cluster()
        s = Spinner()
        log.log(INFO_NO_NEWLINE, "Waiting for cluster to start...")
        s.start()
        while True:
            if self.is_cluster_up():
                s.stop()
                break
            else:  
                time.sleep(15)

        log.info("The master node is %s" % self.master_node.dns_name)

        if self.VOLUME:
            self.attach_volume_to_master()

        log.info("Setting up the cluster...")
        setup = self._setup_class(self)
        setup.run()
            
        log.info("""

The cluster has been started and configured. ssh into the master node as root by running: 

$ starcluster sshmaster %(tag)s

or as %(user)s directly:

$ ssh -i %(key)s %(user)s@%(master)s

        """ % {
            'master': self.master_node.dns_name, 
            'user': self.CLUSTER_USER, 
            'key': self.KEY_LOCATION,
            'tag': self.CLUSTER_TAG,
        })

    def is_valid(self): 
        CLUSTER_SIZE = self.CLUSTER_SIZE
        KEYNAME = self.KEYNAME
        KEY_LOCATION = self.KEY_LOCATION
        if not self._has_all_required_settings():
            log.error('Please specify the required settings')
            return False
        if not self._has_valid_credentials():
            log.error('Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination. Please check your settings')
            return False
        if not self._has_keypair():
            log.error('Account does not contain a key with KEYNAME = %s. Please check your settings' % KEYNAME)
            return False
        if not os.path.exists(KEY_LOCATION):
            log.error('KEY_LOCATION=%s does not exist. Please check your settings' % KEY_LOCATION)
            return False
        elif not os.path.isfile(KEY_LOCATION):
            log.error('KEY_LOCATION=%s is not a file. Please check your settings' % KEY_LOCATION)
            return False
        if CLUSTER_SIZE <= 0:
            log.error('CLUSTER_SIZE must be a positive integer. Please check your settings')
            return False
        if not self._has_valid_zone():
            log.error('Your AVAILABILITY_ZONE setting is invalid. Please check your settings')
            return False
        if not self._has_valid_ebs_settings():
            log.error('EBS settings are invalid. Please check your settings')
            return False
        if not self._has_valid_image_settings():
            log.error('Your MASTER_IMAGE_ID/NODE_IMAGE_ID setting(s) are invalid. Please check your settings')
            return False
        if not self._has_valid_instance_type_settings():
            log.error('Your INSTANCE_TYPE setting is invalid. Please check your settings')
            return False
        if not self._has_valid_shell_setting():
            log.error('Your CLUSTER_SHELL setting %s is invalid. Please check your settings' % self.CLUSTER_SHELL)
        return True

    def _has_valid_shell_setting(self):
        CLUSTER_SHELL = self.CLUSTER_SHELL
        if not self.__available_shells.get(CLUSTER_SHELL):
            return False
        return True

    def _has_valid_image_settings(self):
        MASTER_IMAGE_ID = self.MASTER_IMAGE_ID
        NODE_IMAGE_ID = self.NODE_IMAGE_ID
        conn = self.ec2
        try:
            image = conn.get_image(NODE_IMAGE_ID)
        except boto.exception.EC2ResponseError,e:
            log.error('NODE_IMAGE_ID %s does not exist' % NODE_IMAGE_ID)
            return False
        if MASTER_IMAGE_ID is not None:
            try:
                master_image = conn.get_image(MASTER_IMAGE_ID)
            except boto.exception.EC2ResponseError,e:
                log.error('MASTER_IMAGE_ID %s does not exist' % MASTER_IMAGE_ID)
                return False
        return True

    def _has_valid_zone(self):
        conn = self.ec2
        AVAILABILITY_ZONE = self.AVAILABILITY_ZONE
        if AVAILABILITY_ZONE:
            try:
                zone = conn.get_zone(AVAILABILITY_ZONE)
                if zone.state != 'available':
                    log.error('The AVAILABILITY_ZONE = %s is not available at this time')
                    return False
            except boto.exception.EC2ResponseError,e:
                log.error('AVAILABILITY_ZONE = %s does not exist' % AVAILABILITY_ZONE)
                return False
        return True

    def _has_valid_instance_type_settings(self):
        MASTER_IMAGE_ID = self.MASTER_IMAGE_ID
        NODE_IMAGE_ID = self.NODE_IMAGE_ID
        INSTANCE_TYPE = self.INSTANCE_TYPE
        instance_types = self.__instance_types
        conn = self.ec2
        if not instance_types.has_key(INSTANCE_TYPE):
            log.error("You specified an invalid INSTANCE_TYPE %s \nPossible options are:\n%s" % (INSTANCE_TYPE,' '.join(instance_types.keys())))
            return False

        try:
            node_image_platform = conn.get_image(NODE_IMAGE_ID).architecture
        except boto.exception.EC2ResponseError,e:
            node_image_platform = None

        instance_platform = instance_types[INSTANCE_TYPE]
        if instance_platform != node_image_platform:
            log.error('You specified an incompatible NODE_IMAGE_ID and INSTANCE_TYPE')
            log.error('INSTANCE_TYPE = %(instance_type)s is for a %(instance_platform)s \
    platform while NODE_IMAGE_ID = %(node_image_id)s is a %(node_image_platform)s platform' \
                        % { 'instance_type': INSTANCE_TYPE, 'instance_platform': instance_platform, \
                            'node_image_id': NODE_IMAGE_ID, 'node_image_platform': node_image_platform})
            return False
        
        if MASTER_IMAGE_ID is not None:
            try:
                master_image_platform = conn.get_image(MASTER_IMAGE_ID).architecture
            except boto.exception.EC2ResponseError,e:
                master_image_platform = None
            if instance_platform != master_image_platform:
                log.error('You specified an incompatible MASTER_IMAGE_ID and INSTANCE_TYPE')
                log.error('INSTANCE_TYPE = %(instance_type)s is for a %(instance_platform)s \
    platform while MASTER_IMAGE_ID = %(master_image_id)s is a %(master_image_platform)s platform' \
                            % { 'instance_type': INSTANCE_TYPE, 'instance_platform': instance_platform, \
                                'image_id': MASETER_IMAGE_ID, 'master_image_platform': master_image_platform})
                return False
        
        return True

    def _has_valid_ebs_settings(self):
        #TODO check that VOLUME id exists
        VOLUME = self.VOLUME
        VOLUME_DEVICE = self.VOLUME_DEVICE
        VOLUME_PARTITION = self.VOLUME_PARTITION
        AVAILABILITY_ZONE = self.AVAILABILITY_ZONE
        conn = self.ec2
        if VOLUME is not None:
            try:
                vol = conn.get_volume(VOLUME)
            except boto.exception.EC2ResponseError,e:
                log.error('VOLUME = %s does not exist' % VOLUME)
                return False
            if VOLUME_DEVICE is None:
                log.error('Must specify VOLUME_DEVICE when specifying VOLUME setting')
                return False
            if VOLUME_PARTITION is None:
                log.error('Must specify VOLUME_PARTITION when specifying VOLUME setting')
                return False
            if AVAILABILITY_ZONE is not None:
                if vol.zone != AVAILABILITY_ZONE:
                    log.error('The VOLUME you specified is only available in region %(vol_zone)s, \
    however, you specified AVAILABILITY_ZONE = %(availability_zone)s\nYou need to \
    either change AVAILABILITY_ZONE or create a new volume in %(availability_zone)s' \
                                % {'vol_zone': vol.region.name, 'availability_zone': AVAILABILITY_ZONE})
                    return False
        return True

    def _has_all_required_settings(self):
        has_all_required = True
        for opt in self.__cluster_settings:
            requirements = self.__cluster_settings[opt]
            name = opt; required = requirements[1];
            if required and self.get(name) is None:
                log.warn('Missing required setting %s' % name)
                has_all_required = False
        return has_all_required

    def _has_valid_credentials(self):
        try:
            self.ec2.get_all_instances()
            return True
        except boto.exception.EC2ResponseError,e:
            return False

    def _has_keypair(self):
        KEYNAME = self.KEYNAME
        conn = self.ec2
        try:
            keypair = conn.get_keypair(KEYNAME)
            return True
        except boto.exception.EC2ResponseError,e:
            return False

if __name__ == "__main__":
    from starcluster.config import StarClusterConfig
    cfg = StarClusterConfig(); cfg.load()
    sc =  cfg.get_cluster('smallcluster')
    if sc.is_valid():
        sc.start(create=True)
