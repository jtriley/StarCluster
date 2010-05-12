#!/usr/bin/env python
import os
import re
import time
import string
import platform
import pprint 
import inspect
import cPickle

from starcluster import ssh
from starcluster import awsutils
from starcluster import clustersetup
from starcluster import static
from starcluster import exception
from starcluster import utils
from starcluster.utils import print_timing
from starcluster.spinner import Spinner
from starcluster.logger import log, INFO_NO_NEWLINE
from starcluster.node import Node

def get_cluster(cluster_name, cfg):
    """Factory for Cluster class"""
    try:
        ec2 = cfg.get_easy_ec2()
        cluster = ec2.get_security_group(_get_cluster_name(cluster_name))
        kwargs = {}
        kwargs.update(cfg.aws)
        try:
            cluster_key = cluster.instances()[0].key_name
            key = cfg.get_key(cluster_key)
        except IndexError:
            key = dict(keyname=None, key_location=None)
        kwargs.update(key)
        kwargs.update({'cluster_tag': cluster_name})
        return Cluster(**kwargs)
    except exception.SecurityGroupDoesNotExist,e:
        raise exception.ClusterDoesNotExist(cluster_name)

def get_cluster_or_none(cluster_name,cfg):
    """
    Same as get_cluster only returns None instead of throwing an exception
    if the cluster is not found
    """
    try:
        return get_cluster(cluster_name, cfg)
    except Exception,e:
        pass

def cluster_exists(tag_name, cfg):
    return get_cluster_or_none(tag_name, cfg) is not None

def ssh_to_master(cluster_name, cfg, user='root'):
    cluster = get_cluster(cluster_name, cfg)
    master = cluster.master_node
    key = cfg.get_key(master.key_name)
    os.system('ssh -i %s %s@%s' % (key.key_location, user,
                                   master.dns_name))
def _get_node_number(alias):
    """
    Maps aliases master, node001, etc to 0,1,etc

    Returns an integer (>=0) representing the node "number" if successful, 
    and returns None otherwise
    """
    if alias == "master":
        return 0
    else:
        pattern = re.compile(r"node([0-9][0-9][0-9])")
        if pattern.match(alias) and len(alias) == 7:
            return int(pattern.match(alias).groups()[0])

def ssh_to_cluster_node(cluster_name, node_id, cfg, user='root'):
    cluster = get_cluster(cluster_name, cfg)
    node_num = _get_node_number(node_id)
    if node_num is None:
        node_num = node_id
    node = None
    try:
        node = cluster.nodes[int(node_num)]
    except:
        if node_id.startswith('i-') and len(node_id) == 10:
            node = cluster.get_node_by_id(node_id)
        else:
            node = cluster.get_node_by_dns_name(node_id)
    if node:
        key = cfg.get_key(node.key_name)
        os.system('ssh -i %s %s@%s' % (key.key_location, user,
                                       node.dns_name))
    else:
        log.error("node '%s' does not exist" % node_id)

def _get_cluster_name(cluster_name):
    if not cluster_name.startswith(static.SECURITY_GROUP_PREFIX):
        cluster_name = static.SECURITY_GROUP_TEMPLATE % cluster_name
    return cluster_name

def stop_cluster(cluster_name, cfg):
    ec2 = cfg.get_easy_ec2()
    cname = _get_cluster_name(cluster_name)
    try:
        cluster = ec2.get_security_group(cname)
        for node in cluster.instances():
            log.info('Shutting down %s' % node.id)
            node.stop()
        log.info('Removing cluster security group %s' % cluster.name)
        cluster.delete()
    except exception.SecurityGroupDoesNotExist,e:
        raise exception.ClusterDoesNotExist(cluster_name)

def get_cluster_security_groups(cfg):
    ec2 = cfg.get_easy_ec2()
    sgs = ec2.get_security_groups()
    starcluster_groups = []
    for sg in sgs:
        is_starcluster = sg.name.startswith(static.SECURITY_GROUP_PREFIX)
        if is_starcluster and sg.name != static.MASTER_GROUP:
            starcluster_groups.append(sg)
    return starcluster_groups

def get_tag_from_sg(sg):
    """
    Returns the cluster tag name from a security group name that starts with
    static.SECURITY_GROUP_PREFIX

    Example:
        sg = '@sc-mycluster'
        print get_tag_from_sg(sg)
        mycluster
    """
    regex = re.compile(static.SECURITY_GROUP_PREFIX + '-(.*)')
    match = regex.match(sg)
    if match:
        return match.groups()[0]

def list_clusters(cfg):
    starcluster_groups = get_cluster_security_groups(cfg)
    if starcluster_groups:
        for scg in starcluster_groups:
            print
            tag = get_tag_from_sg(scg.name)
            header = '%s (security group: %s)' % (tag, scg.name)
            print '-'*len(header)
            print header
            print '-'*len(header)
            cl = get_cluster(tag, cfg)
            master = cl.master_node
            print 'Launch time: %s' % master.launch_time
            print 'Zone: %s' % master.placement
            print 'Keypair: %s' % master.key_name
            if master.block_device_mapping:
                print 'EBS volumes:'
                devices = master.block_device_mapping
                for dev in devices:
                    d = devices.get(dev)
                    vol_id = d.volume_id
                    status = d.status
                    print '    %s on master:%s (status: %s)' % (vol_id, dev, status)
            if cl.nodes:
                print 'Cluster nodes:'
            for node in cl.nodes:
                spot = node.spot_id or ''
                if spot:
                    spot = '(spot %s)' % spot
                print "    %7s %s %s %s %s" % (node.alias, node.state, node.id,
                                               node.dns_name, spot)
    else:
        log.info("No clusters found...")

def run_plugin(plugin_name, cluster_tag, cfg):
    ec2 = cfg.get_easy_ec2()
    cl = get_cluster(cluster_tag)
    cl.load_receipt()
    plug = cfg.get_plugin(plugin_name)
    plugins = {}
    plugins[plugin_name] = plug
    plugins = cl.load_plugins(plugins)
    master = cl.master_node
    for p in plugins:
        p.run(cl.nodes, cl.master_node, cl.cluster_user, cl.cluster_shell, 
              volumes)

class Cluster(object):
    def __init__(self,
            aws_access_key_id=None,
            aws_secret_access_key=None,
            aws_port=None,
            aws_is_secure=True,
            aws_ec2_path='/',
            aws_s3_path='/',
            aws_region_name=None,
            aws_region_host=None,
            spot_bid=None,
            cluster_tag=None,
            cluster_description=None,
            cluster_size=None,
            cluster_user=None,
            cluster_shell=None,
            master_image_id=None,
            master_instance_type=None,
            node_image_id=None,
            node_instance_type=None,
            availability_zone=None,
            keyname=None,
            key_location=None,
            volumes=[],
            plugins=[],
            **kwargs):

        now = time.strftime("%Y%m%d%H%M")

        self.ec2 = awsutils.EasyEC2(
            aws_access_key_id, aws_secret_access_key,
            aws_port = aws_port, aws_is_secure = aws_is_secure,
            aws_ec2_path = aws_ec2_path, aws_s3_path = aws_s3_path,
            aws_region_name = aws_region_name, 
            aws_region_host = aws_region_host,
        )
        self.spot_bid = spot_bid
        self.cluster_tag = cluster_tag
        self.cluster_description = cluster_description
        if self.cluster_tag is None:
            self.cluster_tag = now
        if cluster_description is None:
            self.cluster_description = "Cluster created at %s" % now 
        self.cluster_size = cluster_size
        self.cluster_user = cluster_user
        self.cluster_shell = cluster_shell
        self.master_image_id = master_image_id
        self.master_instance_type = master_instance_type
        self.node_image_id = node_image_id
        self.node_instance_type = node_instance_type
        self.availability_zone = availability_zone
        self.keyname = keyname
        self.key_location = key_location
        self.volumes = self.load_volumes(volumes)
        self.plugins = plugins

        self.__instance_types = static.INSTANCE_TYPES
        self.__cluster_settings = static.CLUSTER_SETTINGS
        self.__available_shells = static.AVAILABLE_SHELLS
        self._master_reservation = None
        self._node_reservation = None
        self._nodes = None
        self._master = None
        self._plugins = self.load_plugins(plugins)
        self._zone = None

    @property
    def zone(self):
        """
        If volumes are specified, this method determines the common availability
        zone between those volumes. If an availability zone is explicitly
        specified in the config and does not match the common availability zone
        of the volumes, an exception is raised. If all volumes are not in the same
        availabilty zone an exception is raised. If no volumes are specified,
        returns the user specified availability zone if it exists.
        """
        if not self._zone:
            zone = None
            if self.availability_zone:
                zone = self.ec2.get_zone(self.availability_zone).name
            common_zone = None
            for volume in self.volumes:
                volid = self.volumes.get(volume).get('volume_id')
                vol = self.ec2.get_volume(volid)
                if not common_zone:
                    common_zone = vol.zone
                elif vol.zone != common_zone:
                    vols = [ self.volumes.get(v).get('volume_id') 
                         for v in self.volumes ]
                    raise exception.VolumesZoneError(vols)
            if common_zone and zone and zone != common_zone:
                raise exception.InvalidZone(zone, common_zone)
            if not zone and common_zone:
                zone = common_zone
            self._zone=zone
        return self._zone

    def load_volumes(self, vols):
        """
        Iterate through vols and set device/partition settings automatically if
        not specified.

        This method assigns the first volume to /dev/sdz, second to /dev/sdy,
        etc for all volumes that do not include a device/partition setting
        """
        devices = [ '/dev/sd%s' % s for s in string.lowercase ]
        for volname in vols:
            vol = vols.get(volname)
            dev = vol.get('device')
            if dev in devices:
                # rm user-defined devices from the list of auto-assigned devices
                devices.remove(dev)
        volumes = {}
        for volname in vols:
            vol = vols.get(volname)
            device = vol.get('device')
            if not device:
                device = devices.pop()
            if not utils.is_valid_device(device):
                raise exception.InvalidDevice(device)
            v = volumes[volname] = utils.AttributeDict()
            v.update(vol)
            v['device'] = device
            part = vol.get('partition',1)
            partition = device + str(part)
            if not utils.is_valid_partition(partition):
                raise exception.InvalidPartition(part)
            v['partition'] = partition
        return volumes

    def load_plugins(self, plugins):
        plugs = []
        for plugin in plugins:
            setup_class = plugin.get('setup_class')
            plugin_name = plugin.get('__name__')
            mod_name = '.'.join(setup_class.split('.')[:-1])
            class_name = setup_class.split('.')[-1]
            try:
                mod = __import__(mod_name, globals(), locals(), [class_name])
            except SyntaxError,e:
                raise exception.PluginSyntaxError(
                    "Plugin %s (%s) contains a syntax error at line %s" % \
                    (plugin_name, e.filename, e.lineno)
                )
            except ImportError,e:
                raise exception.PluginLoadError(
                    "Failed to import plugin %s: %s" % (plugin_name, e.message)
                )
            klass = getattr(mod, class_name, None)
            if klass:
                if issubclass(klass, clustersetup.ClusterSetup):
                    argspec = inspect.getargspec(klass.__init__)
                    args = argspec.args[1:]
                    nargs = len(args)
                    ndefaults = 0
                    if argspec.defaults:
                        ndefaults = len(argspec.defaults)
                    nrequired = nargs - ndefaults
                    config_args = []
                    for arg in argspec.args:
                        if arg in plugin:
                            config_args.append(plugin.get(arg))
                    log.debug("config_args = %s" % config_args)
                    log.debug("args = %s" % argspec.args)
                    if nrequired != len(config_args):
                        raise exception.PluginError(
                        "Not enough settings provided for plugin %s" % \
                            plugin_name
                        )
                    plugs.append((plugin_name,klass(*config_args)))
                else:
                    raise exception.PluginError(
"""Plugin %s must be a subclass of starcluster.clustersetup.ClusterSetup""" \
                                               % setup_class)
            else:
                raise exception.PluginError(
                    'Plugin class %s does not exist' % setup_class
                )
        return plugs

    def update(self, kwargs):
        for key in kwargs.keys():
            if hasattr(self, key):
                self.__dict__[key] = kwargs[key]

    def _validate_running_instances(self):
        """
        Validate existing instances against this template's settings 
        """
        self._validate_instance_types()
        num_running = len(self.nodes)
        if num_running != self.cluster_size:
            raise exception.ClusterValidationError(
                "Number of pending/running instances (%s) != %s" % \
                (num_running, self.cluster_size))
        mtype = self.master_node.instance_type
        mastertype = self.master_instance_type or self.node_instance_type
        if mtype != mastertype:
            raise exception.ClusterValidationError(
                "The running master node's instance type (%s) != %s" % \
                (mtype, mastertype))
        masterimage = self.master_image_id or self.node_image_id
        mimage = self.master_node.image_id
        if mimage != masterimage:
            raise exception.ClusterValidationError(
                "The running master node's image id (%s) != %s" % \
                (mimage, masterimage))
        mkey = self.master_node.key_name
        if mkey != self.keyname:
            raise exception.ClusterValidationError(
                "The running master's keypair (%s) != %s" % \
                (mkey, self.keyname))
        try:
            nodes = self.nodes[1:self.cluster_size]
        except IndexError,e:
            raise exception.ClusterValidationError("Cluster has no running instances")
        mazone = self.master_node.placement
        for n in nodes:
            ntype = n.instance_type
            if ntype != self.node_instance_type:
                raise exception.ClusterValidationError(
                    "Running node's instance type (%s) != %s" % \
                    (ntype, self.node_instance_type))
            nimage = n.image_id
            if nimage != self.node_image_id:
                raise exception.ClusterValidationError(
                    "Running node's image id (%s) != %s" % \
                    (nimage, self.node_image_id))
            if n.key_name != self.keyname:
                raise exception.ClusterValidationError(
                    "Running node's key_name (%s) != %s" % \
                    (n.key_name, self.keyname))
            nazone = n.placement
            if mazone != nazone:
                raise exception.ClusterValidationError(
                    "Running master zone (%s) does not match node zone (%s)" % \
                    (mazone, nazone))
        # reset zone 
        self._zone = None
        if self.zone and self.zone != mazone:
            raise exception.ClusterValidationError(
                "Running cluster's availability_zone (%s) != %s" % \
                (azone, self.zone))

    def get(self, name):
        return self.__dict__.get(name)

    def __str__(self):
        cfg = {}
        for key in self.__dict__.keys():
            if not key.startswith('_'):
                cfg[key] = getattr(self,key)
        return pprint.pformat(cfg)

    def load_receipt(self):
        """
        Fetch the StarCluster receipt file from the master node and use it to
        populate this object's attributes. This is used to restore the state of
        this object's settings as they were at the time of creating the cluster.
        """
        try:
            f = self.master_node.ssh.remote_file(static.STARCLUSTER_RECEIPT_FILE,'r')
            cfg = cPickle.load(f)
            f.close()
            for key in cfg:
                setattr(self, key, cfg.get(key))
            #self._plugins = self.load_plugins(self.plugins)
            return True
        except IOError,e:
            raise exception.ClusterReceiptError(
                'cluster receipt does not exist')
        except Exception,e:
            raise exception.ClusterReceiptError(
                'failed to load cluster receipt')

    def create_receipt(self):
        """
        Create a 'receipt' file on the master node that contains this Cluster
        object's attributes. This receipt is useful for loading
        the settings used to create the cluster at a later time using
        load_receipt().
        """
        try:
            cfg = {}
            for key in self.__dict__.keys():
                if not key.startswith('_'):
                    val = getattr(self,key)
                    if type(val) in [str, bool, int, float, list, dict]:
                        cfg[key] = val
                    elif type(val) is utils.AttributeDict:
                        cfg[key] = dict(val)
            self.master_node.ssh.execute('mkdir -p %s' % \
                                    static.STARCLUSTER_RECEIPT_DIR)
            f = self.master_node.ssh.remote_file(static.STARCLUSTER_RECEIPT_FILE)
            cPickle.dump(cfg, f)
            f.close()
        except Exception,e:
            print e
            raise exception.ClusterReceiptError(
                'failed to create cluster receipt')
        return True

    @property
    def _security_group(self):
        return static.SECURITY_GROUP_TEMPLATE % self.cluster_tag

    @property
    def master_group(self):
        sg = self.ec2.get_or_create_group(static.MASTER_GROUP,
                                          static.MASTER_GROUP_DESCRIPTION)
        return sg

    @property
    def cluster_group(self):
        sg = self.ec2.get_or_create_group(self._security_group,
                                          self.cluster_description,
                                          auth_group_traffic=True)
        return sg
            
    @property
    def master_node(self):
        if not self._master:
            # TODO: do this with reservation group info instead
            mgroup_instances = self.master_group.instances()
            cgroup_instances = [node.id for node in self.cluster_group.instances()]
            for node in mgroup_instances:
                if node.id in cgroup_instances and node.state in ['pending','running']:
                    self._master = Node(node, self.key_location, 'master')
                    break
        return self._master

    @property
    def nodes(self):
        if not self._nodes:
            nodes = self.cluster_group.instances()
            self._nodes = []
            master = self.master_node
            nodeid = 1
            for node in nodes:
                if node.state not in ['pending','running']:
                    continue
                if node.id == master.id:
                    self._nodes.insert(0,master)
                    continue
                self._nodes.append(Node(node, self.key_location, 
                                        'node%.3d' % nodeid))
                nodeid += 1
        else:
            for node in self._nodes:
                log.debug('refreshing instance %s' % node.id)
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

    def run_instances(self, price=None, image_id=None, instance_type='m1.small', 
                      min_count=1, max_count=1, count=1, key_name=None,
                      security_groups=None, launch_group=None,
                      availability_zone_group=None, placement=None):
        conn = self.ec2
        if price:
            return conn.request_spot_instances(price, image_id, 
                                               instance_type=instance_type, 
                                               count=count, 
                                               launch_group=launch_group, 
                                               key_name=key_name, 
                                               security_groups=security_groups, 
                                               availability_zone_group=availability_zone_group,
                                               placement=placement)
        else:
            return conn.run_instances(image_id, instance_type=instance_type, 
                                      min_count=min_count, max_count=max_count, 
                                      key_name=key_name, 
                                      security_groups=security_groups, 
                                      placement=placement)

    def create_cluster(self):
        log.info("Launching a %d-node cluster..." % self.cluster_size)
        if self.master_image_id is None:
            self.master_image_id = self.node_image_id
        if self.master_instance_type is None:
            self.master_instance_type = self.node_instance_type
        log.info("Launching master node...")
        log.info("Master AMI: %s" % self.master_image_id)
        master_sg = self.master_group.name
        cluster_sg = self.cluster_group.name
        zone = self.zone
        master_response = self.run_instances(self.spot_bid,
            image_id=self.master_image_id,
            instance_type=self.master_instance_type,
            min_count=1, max_count=1, count=1,
            key_name=self.keyname,
            security_groups=[master_sg, cluster_sg],
            availability_zone_group=cluster_sg,
            launch_group=cluster_sg,
            placement=zone)
        print master_response
        # Make sure nodes are in same zone as master
        if self.spot_bid:
            launch_spec = master_response[0].launch_specification
            zone = launch_spec.placement
        else:
            zone = master_response.instances[0].placement
        if self.cluster_size > 1:
            log.info("Launching worker nodes...")
            log.info("Node AMI: %s" % self.node_image_id)
            instances_response = self.run_instances(self.spot_bid,
                image_id=self.node_image_id,
                instance_type=self.node_instance_type,
                min_count=max((self.cluster_size-1)/2, 1),
                max_count=max(self.cluster_size-1,1),
                count=max(self.cluster_size-1,1),
                key_name=self.keyname,
                security_groups=[cluster_sg],
                availability_zone_group=cluster_sg,
                launch_group=cluster_sg,
                placement=zone)
            print instances_response

    def is_cluster_up(self):
        """
        Check whether there are cluster_size nodes running,
        that ssh (port 22) is up on all nodes, and that each node
        has an internal ip address associated with it
        """
        nodes = self.running_nodes
        if len(nodes) == self.cluster_size:
            for node in nodes:
                if not node.is_up():
                    return False
            return True
        else:
            return False

    def attach_volumes_to_master(self):
        for vol in self.volumes:
            volume = self.volumes.get(vol)
            device = volume.get('device')
            vol_id = volume.get('volume_id')
            vol = self.ec2.get_volume(vol_id)
            log.info("Attaching volume %s to master node on %s ..." % (vol.id,
                                                                      device))
            if vol.status != "available":
                log.error('Volume %s not available...please check and try again'
                         % vol.id)
                continue
            resp = vol.attach(self.master_node.id, device)
            log.debug("resp = %s" % resp)
            while True:
                vol.update()
                if vol.attachment_state() == 'attached':
                    break
                time.sleep(5)

    def detach_volumes(self):
        for vol in self.volumes:
            vol_id = self.volumes.get(vol).get('volume_id')
            vol = self.ec2.get_volume(vol_id)
            log.info("Detaching volume %s from master" % vol.id)
            vol.detach()

    def stop_cluster(self):
        resp = raw_input(">>> Shutdown cluster ? (yes/no) ")
        if resp == 'yes':
            if self.volumes:
                self.detach_volumes()
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
        while not self.is_cluster_up():
            time.sleep(60)
        s.stop()

        log.info("The master node is %s" % self.master_node.dns_name)

        if self.volumes:
            self.attach_volumes_to_master()

        log.info("Setting up the cluster...")
        default_setup = clustersetup.DefaultClusterSetup().run(
            self.nodes, self.master_node, 
            self.cluster_user, self.cluster_shell, 
            self.volumes
        )
        self.create_receipt()
        for plugin in self._plugins:
            try:
                plugin_name = plugin[0]
                plug = plugin[1]
                log.info("Running plugin %s" % plugin_name)
                plug.run(self.nodes, self.master_node, self.cluster_user,
                              self.cluster_shell, self.volumes)
            except Exception, e:
                log.error("Error occured while running plugin '%s':" % \
                          plugin_name)
                print e
            
        log.info("""

The cluster has been started and configured. 

Login to the master node as root by running: 

    $ starcluster sshmaster %(tag)s

or manually as %(user)s:

    $ ssh -i %(key)s %(user)s@%(master)s

When you are finished using the cluster, run:

    $ starcluster stop %(tag)s

to shutdown the cluster and stop paying for service

        """ % {
            'master': self.master_node.dns_name, 
            'user': self.cluster_user, 
            'key': self.key_location,
            'tag': self.cluster_tag,
        })

    def is_running_valid(self):
        """
        Checks whether the current running instances are compatible
        with this cluster template's settings
        """
        try:
            self._validate_running_instances()
            return True
        except exception.ClusterValidationError,e:
            log.error(e.msg)
            return False

    def is_valid(self):
        """
        Checks that all cluster template settings are valid
        """
        try:
            self._has_all_required_settings()
            self._validate_spot_bid()
            self._validate_cluster_size()
            self._validate_shell_setting()
            self._validate_credentials()
            self._validate_keypair()
            self._validate_zone()
            self._validate_ebs_settings()
            self._validate_ebs_aws_settings()
            self._validate_image_settings()
            self._validate_instance_types()
            return True
        except exception.ClusterValidationError,e:
            log.error(e.msg)
            return False

    def _validate_spot_bid(self):
        if self.spot_bid is not None:
            if type(self.spot_bid) not in [int,float]:
                raise exception.ClusterValidationError( \
                    'spot_bid must be integer or float')
            if self.spot_bid <= 0:
                raise exception.ClusterValidationError(
                    'spot_bid must be an integer or float > 0')
        return True

    def _validate_cluster_size(self):
        if self.cluster_size <= 0 or not isinstance(self.cluster_size, int):
            raise exception.ClusterValidationError(
                'cluster_size must be a positive integer.')
        return True

    def _validate_shell_setting(self):
        cluster_shell = self.cluster_shell
        if not self.__available_shells.get(cluster_shell):
            raise exception.ClusterValidationError(
                'Invalid user shell specified. Options are %s' % \
                ' '.join(self.__available_shells.keys()))
        return True

    def _validate_image_settings(self):
        master_image_id = self.master_image_id
        node_image_id = self.node_image_id
        conn = self.ec2
        image = conn.get_image_or_none(node_image_id)
        if not image or image.id != node_image_id:
            raise exception.ClusterValidationError(
                'node_image_id %s does not exist' % node_image_id
            )
        if master_image_id:
            master_image = conn.get_image_or_none(master_image_id)
            if not master_image or master_image.id != master_image_id:
                raise exception.ClusterValidationError(
                    'master_image_id %s does not exist' % master_image_id)
        return True

    def _validate_zone(self):
        availability_zone = self.availability_zone
        if availability_zone:
            zone = self.ec2.get_zone(availability_zone)
            if not zone:
                raise exception.ClusterValidationError(
                    'availability_zone = %s does not exist' % availability_zone
                )
            if zone.state != 'available':
                log.warn('The availability_zone = %s ' % zone +
                          'is not available at this time')
        return True

    def __check_platform(self, image_id, instance_type):
        """
        Validates whether an image_id (AMI) is compatible with a given
        instance_type. image_id_setting and instance_type_setting are the
        setting labels in the config file.
        """
        image = self.ec2.get_image_or_none(image_id)
        if not image:
            raise exception.ClusterValidationError('Image %s does not exist' %
                                                   image_id)
        image_platform = image.architecture
        instance_platform = self.__instance_types[instance_type]
        if instance_platform != image_platform:
            error_msg = "Instance type %(instance_type)s is for an " + \
                          "%(instance_platform)s platform while " + \
                          "%(image_id)s is an %(image_platform)s platform" 
            error_dict = {'instance_type':instance_type, 
                          'instance_platform': instance_platform, 
                          'image_id': image_id,
                          'image_platform': image_platform}
            raise exception.ClusterValidationError(error_msg % error_dict)
        return True

    def _validate_instance_types(self):
        master_image_id = self.master_image_id
        node_image_id = self.node_image_id
        master_instance_type = self.master_instance_type
        node_instance_type = self.node_instance_type
        instance_types = self.__instance_types
        instance_type_list = ' '.join(instance_types.keys())
        conn = self.ec2
        if not instance_types.has_key(node_instance_type):
            raise exception.ClusterValidationError(
                ("You specified an invalid node_instance_type %s \n" + 
                "Possible options are:\n%s") % \
                (node_instance_type, instance_type_list))
        elif master_instance_type:
            if not instance_types.has_key(master_instance_type):
                raise exception.ClusterValidationError(
                    ("You specified an invalid master_instance_type %s\n" + \
                    "Possible options are:\n%s") % \
                    (master_instance_type, instance_type_list))

        try:
            self.__check_platform(node_image_id, node_instance_type)
        except exception.ClusterValidationError,e:
            raise exception.ClusterValidationError( 
                'Incompatible node_image_id and node_instance_type\n' + e.msg
            )
        if master_image_id and not master_instance_type:
            try:
                self.__check_platform(master_image_id, node_instance_type)
            except exception.ClusterValidationError,e:
                raise exception.ClusterValidationError( 
                    'Incompatible master_image_id and node_instance_type\n' + e.msg
                )
        elif master_image_id and master_instance_type:
            try:
                self.__check_platform(master_image_id, master_instance_type)
            except exception.ClusterValidationError,e:
                raise exception.ClusterValidationError( 
                    'Incompatible master_image_id and master_instance_type\n' + e.msg
                )
        elif master_instance_type and not master_image_id:
            try:
                self.__check_platform(node_image_id, master_instance_type)
            except exception.ClusterValidationError,e:
                raise exception.ClusterValidationError( 
                    'Incompatible node_image_id and master_instance_type\n' + e.msg
                )
        return True

    def _validate_ebs_aws_settings(self):
        """
        Verify EBS volumes exists on Amazon and that each volume's zone matches
        this cluster's zone setting. Requires AWS credentials.
        """
        zone = self.zone
        for vol in self.volumes:
            v = self.volumes.get(vol)
            vol_id = v.get('volume_id')
            vol = self.ec2.get_volume(vol_id)
            if vol.status != 'available':
                msg = "volume %s is not available (status: %s)" % (vol_id,
                                                                   vol.status)
                raise exception.ClusterValidationError(msg)

    def _validate_ebs_settings(self):
        """
        Check EBS vols for missing/duplicate DEVICE/PARTITION/MOUNT_PATHs 
        and validate these settings. Does not require AWS credentials.
        """
        vol_ids = []
        devices = []
        mount_paths = []
        for vol in self.volumes:
            vol_name = vol
            vol = self.volumes.get(vol)
            vol_id = vol.get('volume_id')
            device = vol.get('device')
            partition = vol.get('partition') 
            mount_path = vol.get("mount_path")
            mount_paths.append(mount_path)
            devices.append(device)
            vol_ids.append(vol_id)
            if not device:
                raise exception.ClusterValidationError(
                    'Missing DEVICE setting for volume %s' % vol_name)
            if not utils.is_valid_device(device):
                raise exception.ClusterValidationError(
                    "Invalid DEVICE value for volume %s" % vol_name)
            if not partition:
                raise exception.ClusterValidationError(
                    'Missing PARTITION setting for volume %s' % vol_name)
            if not utils.is_valid_partition(partition):
                raise exception.ClusterValidationError(
                    "Invalid PARTITION value for volume %s" % vol_name)
            if not partition.startswith(device):
                raise exception.ClusterValidationError(
                    "Volume PARTITION must start with %s" % device)
            if not mount_path:
                raise exception.ClusterValidationError(
                    'Missing MOUNT_PATH setting for volume %s' % vol_name)
            if not mount_path.startswith('/'):
                raise exception.ClusterValidationError(
                    "MOUNT_PATH for volume %s should start with /" % vol_name)
        for vol_id in vol_ids:
            if vol_ids.count(vol_id) > 1:
                raise exception.ClusterValidationError(
                    ("Multiple configurations for volume %s specified. " + \
                    "Please choose one") % vol_id)
        for dev in devices:
            if devices.count(dev) > 1:
                raise exception.ClusterValidationError(
                    "Can't attach more than one volume on device %s" % dev)
        for path in mount_paths:
            if mount_paths.count(path) > 1:
                raise exception.ClusterValidationError(
                    "Can't mount more than one volume on %s" % path)
        return True

    def _has_all_required_settings(self):
        has_all_required = True
        for opt in self.__cluster_settings:
            requirements = self.__cluster_settings[opt]
            name = opt; required = requirements[1];
            if required and self.get(name.lower()) is None:
                log.warn('Missing required setting %s' % name)
                has_all_required = False
        return has_all_required

    def _validate_credentials(self):
        if not self.ec2.is_valid_conn():
            raise exception.ClusterValidationError(
                'Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination.')
        return True

    def _validate_keypair(self):
        key_location = self.key_location
        if not os.path.exists(key_location):
            raise exception.ClusterValidationError(
                'key_location=%s does not exist.' % \
                key_location)
        elif not os.path.isfile(key_location):
            raise exception.ClusterValidationError(
                'key_location=%s is not a file.' % \
                key_location)
        keyname = self.keyname
        conn = self.ec2
        keypair = self.ec2.get_keypair_or_none(keyname)
        if not keypair:
            raise exception.ClusterValidationError(
                'Account does not contain a key with keyname = %s. ' % keyname)
        if self.zone:
            z = self.ec2.get_zone(self.zone)
            if keypair.region != z.region:
                raise exception.ClusterValidationError(
                    'Keypair %s not in availability zone region %s' % (keyname,
                                                                       z.region))
        return True

if __name__ == "__main__":
    from starcluster.config import StarClusterConfig
    cfg = StarClusterConfig(); cfg.load()
    sc =  cfg.get_cluster_template('smallcluster', 'mynewcluster')
    if sc.is_valid():
        sc.start(create=True)
