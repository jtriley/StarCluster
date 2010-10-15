#!/usr/bin/env python
import os
import re
import time
import string
import pprint
import inspect
import cPickle

from starcluster import utils
from starcluster import static
from starcluster import managers
from starcluster import exception
from starcluster import clustersetup
from starcluster.templates import user_msgs
from starcluster.utils import print_timing
from starcluster.spinner import Spinner
from starcluster.logger import log, INFO_NO_NEWLINE
from starcluster.node import Node


class ClusterManager(managers.Manager):
    """
    Manager class for Cluster objects
    """
    def __repr__(self):
        return "<ClusterManager: %s>" % self.ec2.conn.region.name

    def get_cluster(self, cluster_name, load_plugins=True):
        """
        Returns a Cluster object representing an active cluster
        """
        try:
            clname = self._get_cluster_name(cluster_name)
            self.ec2.get_security_group(clname)
            cl = Cluster(ec2_conn=self.ec2, cluster_tag=cluster_name)
            cl.load_receipt(load_plugins=load_plugins)
            try:
                key_location = self.cfg.get_key(cl.keyname).get('key_location')
                cl.key_location = key_location
            except (exception.KeyNotFound, Exception):
                pass
            return cl
        except exception.SecurityGroupDoesNotExist:
            raise exception.ClusterDoesNotExist(cluster_name)

    def get_default_cluster_template(self, tag):
        """
        Returns name of the default cluster template defined in the config
        """
        return self.cfg.get_default_cluster_template(tag)

    def get_cluster_template(self, template_name, tag_name=None):
        """
        Returns a new Cluster object using the settings from the cluster
        template template_name

        If tag_name is passed, the Cluster object's cluster_tag setting will
        be set to tag_name
        """
        cl = self.cfg.get_cluster_template(template_name, tag_name=tag_name,
                                           ec2_conn=self.ec2)
        return cl

    def get_cluster_or_none(self, cluster_name):
        """
        Same as get_cluster but returns None instead of throwing an exception
        if the cluster does not exist
        """
        try:
            return self.get_cluster(cluster_name)
        except exception.ClusterDoesNotExist:
            pass

    def cluster_exists(self, tag_name):
        """
        Returns True if cluster exists
        """
        return self.get_cluster_or_none(tag_name) is not None

    def ssh_to_master(self, cluster_name, user='root'):
        """
        ssh to master node of cluster_name

        user keyword specifies an alternate user to login as
        """
        cluster = self.get_cluster(cluster_name)
        cluster.ssh_to_master(user=user)

    def ssh_to_cluster_node(self, cluster_name, node_id, user='root'):
        """
        ssh to a node in cluster_name that has either an id,
        dns name, or alias matching node_id

        user keyword specifies an alternate user to login as
        """
        cluster = self.get_cluster(cluster_name)
        cluster.ssh_to_node(node_id, user=user)

    def _get_cluster_name(self, cluster_name):
        """
        Returns human readable cluster name/tag prefixed with '@sc-'
        """
        if not cluster_name.startswith(static.SECURITY_GROUP_PREFIX):
            cluster_name = static.SECURITY_GROUP_TEMPLATE % cluster_name
        return cluster_name

    def stop_cluster(self, cluster_name):
        """
        Stops cluster_name if it's an EBS cluster, otherwise terminates the
        cluster
        """
        cl = self.get_cluster(cluster_name)
        cl.stop_cluster()

    def terminate_cluster(self, cluster_name):
        """
        Terminates cluster_name
        """
        cl = self.get_cluster(cluster_name)
        cl.terminate_cluster()

    def get_cluster_security_group(self, group_name):
        """
        Return all security groups on EC2 that start with '@sc-'
        """
        gname = self._get_cluster_name(group_name)
        return self.ec2.get_security_group(gname)

    def get_cluster_security_groups(self):
        """
        Return all security groups on EC2 that start with '@sc-'
        """
        glob = static.SECURITY_GROUP_TEMPLATE % '*'
        sgs = self.ec2.get_security_groups(filters={'group-name': glob})
        return sgs

    def get_tag_from_sg(self, sg):
        """
        Returns the cluster tag name from a security group name that starts
        with static.SECURITY_GROUP_PREFIX

        Example:
            sg = '@sc-mycluster'
            print get_tag_from_sg(sg)
            mycluster
        """
        regex = re.compile(static.SECURITY_GROUP_PREFIX + '-(.*)')
        match = regex.match(sg)
        if match:
            return match.groups()[0]

    def list_clusters(self, cluster_groups=None):
        """
        Prints a summary for each active cluster on EC2
        """
        if not cluster_groups:
            cluster_groups = self.get_cluster_security_groups()
            if not cluster_groups:
                log.info("No clusters found...")
        else:
            cluster_groups = [self.get_cluster_security_group(g) for g \
                              in cluster_groups]

        for scg in cluster_groups:
            tag = self.get_tag_from_sg(scg.name)
            cl = self.get_cluster(tag, load_plugins=False)
            header = '%s (security group: %s)' % (tag, scg.name)
            print '-' * len(header)
            print header
            print '-' * len(header)
            nodes = cl.nodes
            try:
                n = nodes[0]
            except IndexError:
                n = None
            print 'Launch time: %s' % getattr(n, 'launch_time', 'N/A')
            print 'Zone: %s' % getattr(n, 'placement', 'N/A')
            print 'Keypair: %s' % getattr(n, 'key_name', 'N/A')
            print 'EBS volumes:'
            ebs_nodes = [n for n in nodes if n.attached_vols]
            if ebs_nodes:
                for node in ebs_nodes:
                    devices = node.attached_vols
                    node_id = node.alias or node.id
                    for dev in devices:
                        d = devices.get(dev)
                        vol_id = d.volume_id
                        status = d.status
                        print '    %s on %s:%s (status: %s)' % \
                                (vol_id, node_id, dev, status)
            else:
                print '    No EBS volumes attached...'
            print 'Spot requests:'
            if cl.spot_bid:
                for spot in cl.spot_requests:
                    lspec = spot.launch_specification
                    template = "    %s (ami: %s, type: %s, bid: $%.2f)"
                    print template % (spot.id, lspec.image_id,
                                      lspec.instance_type, spot.price)
            else:
                print '    No spot requests found...'
            print 'Cluster nodes:'
            if nodes:
                for node in nodes:
                    spot = node.spot_id or ''
                    if spot:
                        spot = '(spot %s)' % spot
                    print "    %7s %s %s %s %s" % (node.alias, node.state,
                                                   node.id, node.dns_name,
                                                   spot)
            else:
                print '    No pending/running nodes found...'
            print

    def run_plugin(self, plugin_name, cluster_tag):
        """
        Run a plugin defined in the config.

        plugin_name must match the plugin's section name in the config
        cluster_tag specifies the cluster to run the plugin on
        """
        cl = self.get_cluster(cluster_tag)
        plugs = [self.cfg.get_plugin(plugin_name)]
        cl.load_receipt()
        name, plugin = cl.load_plugins(plugs)[0]
        cl.run_plugin(plugin, name)


class Cluster(object):
    def __init__(self,
            ec2_conn=None,
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
            node_instance_types=[],
            availability_zone=None,
            keyname=None,
            key_location=None,
            volumes=[],
            plugins=[],
            permissions=[],
            **kwargs):

        now = time.strftime("%Y%m%d%H%M")

        self.ec2 = ec2_conn
        self.spot_bid = spot_bid
        self.cluster_tag = cluster_tag
        self.cluster_description = cluster_description
        if self.cluster_tag is None:
            self.cluster_tag = "cluster%s" % now
        if cluster_description is None:
            self.cluster_description = "Cluster created at %s" % now
        self.cluster_size = cluster_size or 0
        self.cluster_user = cluster_user
        self.cluster_shell = cluster_shell
        self.master_image_id = master_image_id
        self.master_instance_type = master_instance_type
        self.node_image_id = node_image_id
        self.node_instance_type = node_instance_type
        self.node_instance_types = node_instance_types
        self.availability_zone = availability_zone
        self.keyname = keyname
        self.key_location = key_location
        self.volumes = self.load_volumes(volumes)
        self.plugins = self.load_plugins(plugins)
        self.permissions = permissions

        self.__instance_types = static.INSTANCE_TYPES
        self.__cluster_settings = static.CLUSTER_SETTINGS
        self.__available_shells = static.AVAILABLE_SHELLS
        self.__protocols = static.PROTOCOLS
        self._master_reservation = None
        self._node_reservation = None
        self._nodes = None
        self._master = None
        self._zone = None
        self._plugins = plugins
        self._cluster_group = None
        self._placement_group = None

    def __repr__(self):
        return '<Cluster: %s (%s-node)>' % (self.cluster_tag,
                                            self.cluster_size)

    @property
    def zone(self):
        """
        If volumes are specified, this method determines the common
        availability zone between those volumes. If an availability zone
        is explicitly specified in the config and does not match the common
        availability zone of the volumes, an exception is raised. If all
        volumes are not in the same availabilty zone an exception is raised.
        If no volumes are specified, returns the user specified availability
        zone if it exists.
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
                    vols = [self.volumes.get(v).get('volume_id')
                            for v in self.volumes]
                    raise exception.VolumesZoneError(vols)
            if common_zone and zone and zone != common_zone:
                raise exception.InvalidZone(zone, common_zone)
            if not zone and common_zone:
                zone = common_zone
            self._zone = zone
        return self._zone

    def load_volumes(self, vols):
        """
        Iterate through vols and set device/partition settings automatically if
        not specified.

        This method assigns the first volume to /dev/sdz, second to /dev/sdy,
        etc for all volumes that do not include a device/partition setting
        """
        devices = ['/dev/sd%s' % s for s in string.lowercase]
        for volname in vols:
            vol = vols.get(volname)
            dev = vol.get('device')
            if dev in devices:
                #rm user-defined devices from the list of auto-assigned devices
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
            part = vol.get('partition', 1)
            partition = device + str(part)
            if not utils.is_valid_partition(partition):
                raise exception.InvalidPartition(part)
            v['partition'] = partition
        return volumes

    def load_plugins(self, plugins):
        plugs = []
        for plugin in plugins:
            setup_class = plugin.get('setup_class')
            plugin_name = plugin.get('__name__').split()[-1]
            mod_name = '.'.join(setup_class.split('.')[:-1])
            class_name = setup_class.split('.')[-1]
            try:
                mod = __import__(mod_name, globals(), locals(), [class_name])
            except SyntaxError, e:
                raise exception.PluginSyntaxError(
                    "Plugin %s (%s) contains a syntax error at line %s" % \
                    (plugin_name, e.filename, e.lineno))
            except ImportError, e:
                raise exception.PluginLoadError(
                    "Failed to import plugin %s: %s" % \
                    (plugin_name, e.message))
            klass = getattr(mod, class_name, None)
            if not klass:
                raise exception.PluginError(
                    'Plugin class %s does not exist' % setup_class)
            if not issubclass(klass, clustersetup.ClusterSetup):
                raise exception.PluginError(
                    ("Plugin %s must be a subclass of " + \
                     "starcluster.clustersetup.ClusterSetup") % setup_class)
            (args, varargs,
             keywords, defaults) = inspect.getargspec(klass.__init__)
            log.debug('plugin args = %s' % args)
            log.debug('plugin varargs = %s' % varargs)
            log.debug('plugin keywords = %s' % keywords)
            log.debug('plugin defaults = %s' % str(defaults))
            args = args[1:]  # ignore self
            nargs = len(args)
            ndefaults = 0
            if defaults:
                ndefaults = len(defaults)
            nrequired = nargs - ndefaults
            args = args[:nrequired]
            kwargs = args[nrequired:]
            config_args = []
            for arg in args:
                if arg in plugin:
                    config_args.append(plugin.get(arg))
            config_kwargs = {}
            for arg in kwargs:
                if arg in plugin:
                    config_kwargs[arg] = plugin.get(arg)
            log.debug("config_args = %s" % config_args)
            log.debug("config_kwargs = %s" % config_kwargs)
            if nrequired > len(config_args):
                raise exception.PluginError(
                "Not enough settings provided for plugin %s" % plugin_name)
            plugs.append((plugin_name, klass(*config_args, **config_kwargs)))
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
            nodes = self.nodes[1:]
        except IndexError:
            raise exception.ClusterValidationError(
                "Cluster has no running instances")
        mazone = self.master_node.placement
        id_start = 0
        for itype in self.node_instance_types:
            size = itype['size']
            image = itype['image'] or self.node_image_id
            type = itype['type'] or self.node_instance_type
            for i in range(id_start, id_start + size):
                n = nodes[i]
                ntype = n.instance_type
                if ntype != type:
                    raise exception.ClusterValidationError(
                        "Running node's instance type (%s) != %s" % \
                        (ntype, type))
                nimage = n.image_id
                if nimage != image:
                    raise exception.ClusterValidationError(
                        "Running node's image id (%s) != %s" % \
                        (nimage, image))
                id_start += 1
        for n in nodes[id_start:]:
            ntype = n.instance_type
            if n.instance_type != self.node_instance_type:
                raise exception.ClusterValidationError(
                    "Running node's instance type (%s) != %s" % \
                    (ntype, self.node_instance_type))
            nimage = n.image_id
            if nimage != self.node_image_id:
                raise exception.ClusterValidationError(
                    "Running node's image id (%s) != %s" % \
                    (nimage, image))
        for n in nodes:
            if n.key_name != self.keyname:
                raise exception.ClusterValidationError(
                    "Running node's key_name (%s) != %s" % \
                    (n.key_name, self.keyname))
            nazone = n.placement
            if mazone != nazone:
                raise exception.ClusterValidationError(
                    ("Running master's zone (%s) " + \
                     "does not match node zone (%s)") % \
                    (mazone, nazone))
        # reset zone
        self._zone = None
        if self.zone and self.zone != mazone:
            raise exception.ClusterValidationError(
                "Running cluster's availability_zone (%s) != %s" % \
                (mazone, self.zone))

    def get(self, name):
        return self.__dict__.get(name)

    def __str__(self):
        cfg = self.__getstate__()
        return pprint.pformat(cfg)

    def load_receipt(self, load_plugins=True):
        """
        Load the original settings used to launch this cluster into this
        Cluster object. The settings are loaded from the cluster group's
        description field.
        """
        try:
            pkl_data = self.cluster_group.description
            cluster_settings = cPickle.loads(str(pkl_data)).__dict__
            for key in cluster_settings:
                if hasattr(self, key):
                    setattr(self, key, cluster_settings.get(key))
            if load_plugins:
                self.plugins = self.load_plugins(self._plugins)
            return True
        except (cPickle.PickleError, ValueError, EOFError):
            # TODO raise exception about old version
            return False
        except exception.PluginError, e:
            log.warn(e)
            log.warn("An error occured while loading plugins")
            log.warn("Not running any plugins")
        except Exception, e:
            raise exception.ClusterReceiptError(
                'failed to load cluster receipt: %s' % e)

    def __getstate__(self):
        cfg = {}
        exclude = ['key_location', 'plugins']
        include = ['_zone', '_plugins']
        for key in self.__dict__.keys():
            private = key.startswith('_')
            if (not private or key in include) and not key in exclude:
                val = getattr(self, key)
                if type(val) in [str, unicode, bool, int, float, list, dict]:
                    cfg[key] = val
                elif type(val) is utils.AttributeDict:
                    cfg[key] = dict(val)
        return cfg

    @property
    def _security_group(self):
        return static.SECURITY_GROUP_TEMPLATE % self.cluster_tag

    @property
    def cluster_group(self):
        if self._cluster_group is None:
            sg = self.ec2.get_or_create_group(self._security_group,
                                              cPickle.dumps(self),
                                              auth_ssh=True,
                                              auth_group_traffic=True)
            for p in self.permissions:
                perm = self.permissions.get(p)
                ip_protocol = perm.get('ip_protocol', 'tcp')
                from_port = perm.get('from_port')
                to_port = perm.get('to_port')
                cidr_ip = perm.get('cidr_ip', '0.0.0.0/0')
                if not self.ec2.has_permission(sg, ip_protocol, from_port,
                                               to_port, cidr_ip):
                    log.info("Opening %s port range %s-%s for CIDR %s" %
                             (ip_protocol, from_port, to_port, cidr_ip))
                    sg.authorize(ip_protocol, from_port, to_port, cidr_ip)
            self._cluster_group = sg
        return self._cluster_group

    @property
    def placement_group(self):
        if self._placement_group is None:
            pg = self.ec2.get_or_create_placement_group(self._security_group)
            self._placement_group = pg
        return self._placement_group

    @property
    def master_node(self):
        if not self._master:
            for node in self.nodes:
                if node.is_master():
                    self._master = node
        return self._master

    @property
    def nodes(self):
        if not self._nodes or len(self._nodes) != self.cluster_size:
            states = ['pending', 'running', 'stopping', 'stopped']
            filters = {'group-id': self._security_group,
                       'instance-state-name': states}
            nodes = self.ec2.get_all_instances(filters=filters)
            self._nodes = []
            for node in nodes:
                n = Node(node, self.key_location)
                if n.is_master():
                    self._master = n
                    self._nodes.insert(0, n)
                else:
                    self._nodes.append(n)
            self._nodes.sort(key=lambda n: n.alias)
        else:
            for node in self._nodes:
                log.debug('refreshing instance %s' % node.id)
                node.update()
        return self._nodes

    def get_node_by_dns_name(self, dns_name):
        for node in self.nodes:
            if node.dns_name == dns_name:
                return node

    def get_node_by_id(self, instance_id):
        for node in self.nodes:
            if node.id == instance_id:
                return node

    def get_node_by_alias(self, alias):
        for node in self.nodes:
            if node.alias == alias:
                return node

    def _nodes_in_states(self, states):
        nodes = []
        for node in self.nodes:
            if node.state in states:
                nodes.append(node)
        return nodes

    @property
    def running_nodes(self):
        return self._nodes_in_states(['running'])

    @property
    def stopped_or_running_nodes(self):
        return self._nodes_in_states(['running', 'stopped'])

    @property
    def not_terminated_nodes(self):
        return self._nodes_in_states(['running', 'stopped', 'shutting-down',
                                      'stopping'])

    @property
    def stopped_nodes(self):
        return self._nodes_in_states(['stopped'])

    @property
    def spot_requests(self):
        filters = {'launch.group-id': self._security_group,
                   'state': ['active', 'open']}
        return self.ec2.get_all_spot_requests(filters=filters)

    def _run_instances(self, price=None, image_id=None,
                       instance_type='m1.small', min_count=1, max_count=1,
                       count=1, key_name=None, security_groups=None,
                       launch_group=None, availability_zone_group=None,
                       placement=None, user_data=None, placement_group=None):
        """
        Convenience method for running spot or flat-rate instances
        """
        conn = self.ec2
        if price:
            return conn.request_spot_instances(
                price, image_id, instance_type=instance_type,
                count=count, launch_group=launch_group, key_name=key_name,
                security_groups=security_groups,
                availability_zone_group=availability_zone_group,
                placement=placement, user_data=user_data)
        else:
            return conn.run_instances(image_id, instance_type=instance_type,
                                      min_count=min_count, max_count=max_count,
                                      key_name=key_name,
                                      security_groups=security_groups,
                                      placement=placement,
                                      user_data=user_data,
                                      placement_group=placement_group)

    def create_node(self, alias, image_id=None, instance_type=None, count=1,
                    zone=None, placement_group=None):
        """
        Convenience method for requesting an instance with this cluster's
        settings
        """
        cluster_sg = self.cluster_group.name
        if instance_type in static.CLUSTER_COMPUTE_TYPES:
            placement_group = self.placement_group.name
        return self._run_instances(self.spot_bid,
            image_id=image_id or self.node_image_id,
            instance_type=instance_type or self.node_instance_type,
            min_count=count, max_count=count, count=count,
            key_name=self.keyname,
            security_groups=[cluster_sg],
            availability_zone_group=cluster_sg,
            launch_group=cluster_sg,
            placement=zone or self.zone,
            user_data=alias,
            placement_group=placement_group)

    def _get_launch_map(self):
        """
        Groups all node-aliases that have similar instance types/image ids
        Returns a dictionary that's used to launch all similar instance types
        and image ids in the same request. Example return value:

        {('c1.xlarge', 'ami-a5c02dcc'): ['node001', 'node002'],
         ('m1.large', 'ami-a5c02dcc'): ['node003'],
         ('m1.small', 'ami-17b15e7e'): ['master', 'node005', 'node006'],
         ('m1.small', 'ami-19e17a2b'): ['node004']}
        """
        lmap = {}
        mtype = self.master_instance_type or self.node_instance_type
        mimage = self.master_image_id or self.node_image_id
        lmap[(mtype, mimage)] = ['master']
        id_start = 1
        for itype in self.node_instance_types:
            count = itype['size']
            image_id = itype['image'] or self.node_image_id
            type = itype['type'] or self.node_instance_type
            if not (type, image_id) in lmap:
                lmap[(type, image_id)] = []
            for id in range(id_start, id_start + count):
                alias = 'node%.3d' % id
                log.debug("Adding node: %s (ami: %s, type: %s)..." % \
                        (alias, image_id, type))
                lmap[(type, image_id)].append(alias)
                id_start += 1
        ntype = self.node_instance_type
        nimage = self.node_image_id
        if not (ntype, nimage) in lmap:
            lmap[(ntype, nimage)] = []
        for id in range(id_start, self.cluster_size):
            alias = 'node%.3d' % id
            log.debug("Adding node: %s (ami: %s, type: %s)..." % \
                    (alias, nimage, ntype))
            lmap[(ntype, nimage)].append(alias)
        return lmap

    def _get_type_and_image_id(self, alias):
        """
        Returns (instance_type,image_id) for a given alias based
        on the map returned from self._get_launch_map
        """
        lmap = self._get_launch_map()
        for (type, image) in lmap:
            key = (type, image)
            if alias in lmap.get(key):
                return key

    def _create_flat_rate_cluster(self):
        """
        Launches cluster using flat-rate instances. This method attempts to
        minimize the number of launch requests by grouping nodes of the same
        type/ami and launching each group simulatenously within a single launch
        request. This is especially important for cluster compute instances
        given that Amazon *highly* recommends requesting all CCI in a single
        launch request.
        """
        lmap = self._get_launch_map()
        zone = None
        master_map = None
        for (type, image) in lmap:
            # launch all aliases that match master's itype/image_id
            aliases = lmap.get((type, image))
            if 'master' in aliases:
                master_map = (type, image)
                user_data = '|'.join(aliases)
                for alias in aliases:
                    log.info("Launching %s (ami: %s, type: %s)" % \
                             (alias, image, type))
                master_response = self.create_node(user_data,
                                                   image_id=image,
                                                   instance_type=type,
                                                   count=len(aliases))
                zone = master_response.instances[0].placement
                print master_response
        lmap.pop(master_map)
        if self.cluster_size <= 1:
            return
        for (type, image) in lmap:
            aliases = lmap.get((type, image))
            for alias in aliases:
                log.info("Launching %s (ami: %s, type: %s)" % \
                         (alias, image, type))
            user_data = '|'.join(aliases)
            node_response = self.create_node(user_data,
                                             image_id=image,
                                             instance_type=type,
                                             count=len(aliases),
                                             zone=zone)
            print node_response

    def _create_spot_cluster(self):
        """
        Launches cluster using all spot instances. This method makes a single
        spot request for each node in the cluster since spot instances
        *always* have an ami_launch_index of 0. This is needed in order to
        correctly assign aliases to nodes.
        """
        (mtype, mimage) = self._get_type_and_image_id('master')
        log.info("Launching master node (ami: %s, type: %s)..." % \
                 (mtype, mimage))
        master_response = self.create_node('master',
                                           image_id=mimage,
                                           instance_type=mtype)
        print master_response
        if self.cluster_size <= 1:
            return
        # Make sure nodes are in same zone as master
        launch_spec = master_response[0].launch_specification
        zone = launch_spec.placement
        for id in range(1, self.cluster_size):
            alias = 'node%.3d' % id
            (ntype, nimage) = self._get_type_and_image_id(alias)
            node_response = self.create_node(alias,
                                             image_id=nimage,
                                             instance_type=ntype,
                                             zone=zone)
            print node_response[0]

    def create_cluster(self):
        """
        Launches all EC2 instances based on this cluster's settings.
        """
        log.info("Launching a %d-node cluster..." % self.cluster_size)
        if self.spot_bid:
            self._create_spot_cluster()
        else:
            self._create_flat_rate_cluster()

    def is_ebs_cluster(self):
        """
        Returns true if any instances in the cluster are EBS-backed
        """
        for node in self.nodes:
            if node.is_ebs_backed():
                return True
        return False

    def is_cluster_compute(self):
        """
        Returns true if any instances are a cluster compute type
        """
        lmap = self._get_launch_map()
        for (type, image) in lmap:
            if type in static.CLUSTER_COMPUTE_TYPES:
                return True
        return False

    def is_cluster_up(self):
        """
        Check whether there are cluster_size nodes running,
        that ssh (port 22) is up on all nodes, and that each node
        has an internal ip address associated with it
        """
        nodes = self.running_nodes
        if len(nodes) != self.cluster_size:
            return False
        for node in nodes:
            if not node.is_up():
                return False
        return True

    def is_cluster_stopped(self):
        """
        Check whether there are zero nodes running
        associated with the cluster
        """
        nodes = self.stopped_nodes
        return len(nodes) == self.cluster_size

    def is_cluster_terminated(self):
        """
        Check whether there are zero nodes running
        associated with the cluster
        """
        nodes = self.not_terminated_nodes
        return len(nodes) == 0

    def attach_volumes_to_master(self):
        """
        Attach each volume to the master node
        """
        for vol in self.volumes:
            volume = self.volumes.get(vol)
            device = volume.get('device')
            vol_id = volume.get('volume_id')
            vol = self.ec2.get_volume(vol_id)
            if vol.attach_data.instance_id == self.master_node.id:
                log.info("Volume %s already attached to master...skipping" % \
                         vol.id)
                continue
            if vol.status != "available":
                log.error(('Volume %s not available...' +
                          'please check and try again') % vol.id)
                continue
            log.info("Attaching volume %s to master node on %s ..." % (vol.id,
                                                                       device))
            resp = vol.attach(self.master_node.id, device)
            log.debug("resp = %s" % resp)
            while True:
                vol.update()
                if vol.attachment_state() == 'attached':
                    break
                time.sleep(5)

    def detach_volumes(self):
        """
        Detach all volumes from the master node
        """
        if self.master_node:
            self.master_node.detach_external_volumes()

    def stop_cluster(self):
        """
        Stop this cluster by detaching all volumes, stopping/terminating
        all instances, cancelling all spot requests (if any), and removing this
        cluster's security group.

        If a node is a spot instance, it will be terminated. Spot
        instances can not be 'stopped', they must be terminated.
        """
        if self.volumes:
            self.detach_volumes()
        for node in self.nodes:
            node.shutdown()
        for spot in self.spot_requests:
            if spot.state not in ['cancelled', 'closed']:
                log.info("Cancelling spot instance request: %s" % spot.id)
                spot.cancel()
        if self.spot_bid or not self.is_ebs_cluster():
            log.info("Removing %s security group" % self._security_group)
            self.cluster_group.delete()

    def terminate_cluster(self):
        """
        Stop this cluster by first detaching all volumes, shutting down all
        instances, cancelling all spot requests (if any), removing this
        cluster's placement group (if any), and removing this cluster's
        security group.
        """
        if self.volumes:
            self.detach_volumes()
        for node in self.nodes:
            node.terminate()
        for spot in self.spot_requests:
            if spot.state not in ['cancelled', 'closed']:
                log.info("Cancelling spot instance request: %s" % spot.id)
                spot.cancel()
        log.info("Removing %s security group" % self._security_group)
        self.cluster_group.delete()
        if self.is_cluster_compute():
            pg = self.placement_group
            log.info("Removing %s placement group" % pg.name)
            pg.delete()

    def start(self, create=True, create_only=False, validate=True,
              validate_only=False, validate_running=False):
        """
        Handles creating and configuring a cluster.
        Validates, creates, and configures a cluster.
        Passing validate=False will ignore validate_only and validate_running
        keywords and is effectively the same as running _start
        """
        if validate:
            retval = self._validate(validate_running=validate_running)
            if validate_only:
                return retval
        return self._start(create, create_only)

    @print_timing("Starting cluster")
    def _start(self, create=True, create_only=False):
        """
        Start cluster from this cluster template's settings
        Handles creating and configuring a cluster
        Does not attempt to validate before running
        """
        log.info("Starting cluster...")
        if create:
            mtype = self.master_instance_type or self.node_instance_type
            self.master_instance_type = mtype
            self.create_cluster()
        else:
            for node in self.stopped_nodes:
                log.info("Starting stopped node: %s" % node.alias)
                node.start()
        if create_only:
            return
        s = Spinner()
        log.log(INFO_NO_NEWLINE, "Waiting for cluster to start...")
        s.start()
        while not self.is_cluster_up():
            time.sleep(30)
        s.stop()
        log.info("The master node is %s" % self.master_node.dns_name)
        if self.volumes:
            self.attach_volumes_to_master()
        log.info("Setting up the cluster...")
        clustersetup.DefaultClusterSetup().run(
            self.nodes, self.master_node,
            self.cluster_user, self.cluster_shell,
            self.volumes)
        self.run_plugins()
        log.info(user_msgs.cluster_started_msg % {
            'master': self.master_node.dns_name,
            'user': self.cluster_user,
            'key': self.key_location,
            'tag': self.cluster_tag,
        })

    def run_plugins(self, plugins=None):
        """
        Run all plugins specified in this Cluster object's self.plugins list
        Uses plugins list instead of self.plugins if specified.

        plugins must be a tuple: the first element is the plugin's name, the
        second element is the plugin object (a subclass of ClusterSetup)
        """
        plugs = plugins or self.plugins
        for plug in plugs:
            name, plugin = plug
            self.run_plugin(plugin, name)

    def run_plugin(self, plugin, name=''):
        """
        Run a StarCluster plugin.
        plugin is an instance of the plugin's class
        name is the user-friendly label for the plugin
        """
        plugin_name = name or str(plugin)
        try:
            log.info("Running plugin %s" % plugin_name)
            plugin.run(self.nodes, self.master_node, self.cluster_user,
                       self.cluster_shell, self.volumes)
        except Exception:
            log.error("Error occured while running plugin '%s':" % plugin_name)
            import traceback
            traceback.print_exc()
            log.debug(traceback.format_exc())

    def is_running_valid(self):
        """
        Checks whether the current running instances are compatible
        with this cluster template's settings
        """
        try:
            self._validate_running_instances()
            return True
        except exception.ClusterValidationError, e:
            log.error(e.msg)
            return False

    def _validate(self, validate_running=False):
        """
        Checks that all cluster template settings are valid. Raises
        a ClusterValidationError exception if not. Passing
        validate_running=True will also check that the existing instances
        properties match the configuration of this cluster template.
        """
        log.info("Validating cluster template settings...")
        self._has_all_required_settings()
        self._validate_spot_bid()
        self._validate_cluster_size()
        self._validate_shell_setting()
        self._validate_permission_settings()
        self._validate_credentials()
        self._validate_keypair()
        self._validate_zone()
        self._validate_ebs_settings()
        self._validate_ebs_aws_settings()
        self._validate_image_settings()
        self._validate_instance_types()
        self._validate_cluster_compute()
        if validate_running:
            log.info("Validating existing instances...")
            try:
                self._validate_running_instances()
            except exception.ClusterValidationError:
                log.error('existing instances are not compatible with '
                          'cluster template settings:')
                raise
        log.info('Cluster template settings are valid')
        return True

    def is_valid(self):
        """
        Returns True if all cluster template settings are valid
        """
        try:
            self._validate()
            return True
        except exception.ClusterValidationError, e:
            log.error(e.msg)
            return False

    def _validate_spot_bid(self):
        if self.spot_bid is not None:
            if type(self.spot_bid) not in [int, float]:
                raise exception.ClusterValidationError(
                    'spot_bid must be integer or float')
            if self.spot_bid <= 0:
                raise exception.ClusterValidationError(
                    'spot_bid must be an integer or float > 0')
        return True

    def _validate_cluster_size(self):
        try:
            int(self.cluster_size)
            if self.cluster_size < 1:
                raise ValueError
        except (ValueError, TypeError):
            raise exception.ClusterValidationError(
                'cluster_size must be an integer >= 1')
        num_itypes = sum([i.get('size') for i in self.node_instance_types])
        num_nodes = self.cluster_size - 1
        if num_itypes > num_nodes:
            raise exception.ClusterValidationError(
                ("total number of nodes specified in node_instance_type (%s)" +
                 " must be <= cluster_size-1 (%s)") % (num_itypes, num_nodes))
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
                'node_image_id %s does not exist' % node_image_id)
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
                azone = self.availability_zone
                raise exception.ClusterValidationError(
                    'availability_zone = %s does not exist' % azone)
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
            error_dict = {'instance_type': instance_type,
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
        instance_type_list = ', '.join(instance_types.keys())
        if not node_instance_type in instance_types:
            raise exception.ClusterValidationError(
                ("You specified an invalid node_instance_type %s \n" +
                "Possible options are:\n%s") % \
                (node_instance_type, instance_type_list))
        elif master_instance_type:
            if not master_instance_type in instance_types:
                raise exception.ClusterValidationError(
                    ("You specified an invalid master_instance_type %s\n" + \
                    "Possible options are:\n%s") % \
                    (master_instance_type, instance_type_list))
        try:
            self.__check_platform(node_image_id, node_instance_type)
        except exception.ClusterValidationError, e:
            raise exception.ClusterValidationError(
                'Incompatible node_image_id and node_instance_type\n' + e.msg)
        if master_image_id and not master_instance_type:
            try:
                self.__check_platform(master_image_id, node_instance_type)
            except exception.ClusterValidationError, e:
                raise exception.ClusterValidationError(
                    'Incompatible master_image_id and ' +
                    'node_instance_type\n' + e.msg)
        elif master_image_id and master_instance_type:
            try:
                self.__check_platform(master_image_id, master_instance_type)
            except exception.ClusterValidationError, e:
                raise exception.ClusterValidationError(
                    'Incompatible master_image_id and ' +
                    'master_instance_type\n' + e.msg)
        elif master_instance_type and not master_image_id:
            try:
                self.__check_platform(node_image_id, master_instance_type)
            except exception.ClusterValidationError, e:
                raise exception.ClusterValidationError(
                    'Incompatible node_image_id and ' +
                    'master_instance_type\n' + e.msg)
        for itype in self.node_instance_types:
            type = itype.get('type')
            img = itype.get('image') or node_image_id
            if not type in instance_types:
                raise exception.ClusterValidationError(
                    ("You specified an invalid instance type %s \n" +
                     "Possible options are:\n%s") % (type, instance_type_list))
            try:
                self.__check_platform(img, type)
            except exception.ClusterValidationError, e:
                raise exception.ClusterValidationError(
                    "Invalid settings for node_instance_type %s: %s" %
                    (type, e.msg))
        return True

    def _validate_cluster_compute(self):
        lmap = self._get_launch_map()
        for (type, image) in lmap:
            if type in static.CLUSTER_COMPUTE_TYPES:
                if self.spot_bid:
                    raise exception.ClusterValidationError((
                        'Cluster compute instance type %s ' +
                        'cannot be used with spot instances') % type)
                img = self.ec2.get_image(image)
                if img.virtualizationType != 'hvm':
                    raise exception.ClusterValidationError((
                        'Cluster compute instance type %s ' +
                        'can only be used with HVM images.\n' +
                        'Image %s is *not* an HVM image.') % (type, image))

    def _validate_ebs_aws_settings(self):
        """
        Verify EBS volumes exists on Amazon and that each volume's zone matches
        this cluster's zone setting. Requires AWS credentials.
        """
        for vol in self.volumes:
            v = self.volumes.get(vol)
            vol_id = v.get('volume_id')
            vol = self.ec2.get_volume(vol_id)
            if vol.status != 'available':
                msg = "volume %s is not available (status: %s)" % (vol_id,
                                                                   vol.status)
                raise exception.ClusterValidationError(msg)

    def _validate_permission_settings(self):
        permissions = self.permissions
        for perm in permissions:
            permission = permissions.get(perm)
            protocol = permission.get('ip_protocol')
            if protocol not in self.__protocols:
                raise exception.InvalidProtocol(protocol)
            from_port = permission.get('from_port')
            to_port = permission.get('to_port')
            try:
                from_port = int(from_port)
                to_port = int(to_port)
            except ValueError:
                raise exception.InvalidPortRange(
                    from_port, to_port, reason="integer range required")
            if from_port < 0 or to_port < 0:
                raise exception.InvalidPortRange(
                    from_port, to_port,
                    reason="from/to must be positive integers")
            if from_port > to_port:
                raise exception.InvalidPortRange(
                    from_port, to_port,
                    reason="'from_port' must be <= 'to_port'")
            cidr_ip = permission.get('cidr_ip')
            if not utils.validate_cidr(cidr_ip):
                raise exception.InvalidCIDRSpecified(cidr_ip)

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

    #def _has_all_required_settings(self, settings, object):
        #has_all_required = True
        #for opt in settings:
            #requirements = settings[opt]
            #name = opt; required = requirements[1];
            #if required and object.get(name.lower()) is None:
                #log.warn('Missing required setting %s' % name)
                #has_all_required = False
        #return has_all_required

    def _has_all_required_settings(self):
        has_all_required = True
        for opt in self.__cluster_settings:
            requirements = self.__cluster_settings[opt]
            name = opt
            required = requirements[1]
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
        if not key_location:
            raise exception.ClusterValidationError(
                "no key_location specified for key '%s'" % self.keyname)
        if not os.path.exists(key_location):
            raise exception.ClusterValidationError(
                'key_location=%s does not exist.' % \
                key_location)
        elif not os.path.isfile(key_location):
            raise exception.ClusterValidationError(
                'key_location=%s is not a file.' % \
                key_location)
        keyname = self.keyname
        keypair = self.ec2.get_keypair_or_none(keyname)
        if not keypair:
            raise exception.ClusterValidationError(
                'Account does not contain a key with keyname = %s. ' % keyname)
        if self.zone:
            z = self.ec2.get_zone(self.zone)
            if keypair.region != z.region:
                raise exception.ClusterValidationError(
                    'Keypair %s not in availability zone region %s' % \
                    (keyname, z.region))
        return True

    def ssh_to_master(self, user='root'):
        self.ssh_to_node('master', user=user)

    def ssh_to_node(self, alias, user='root'):
        node = self.get_node_by_alias(alias)
        node = node or self.get_node_by_dns_name(alias)
        node = node or self.get_node_by_id(alias)
        if not node:
            raise exception.InstanceDoesNotExist(alias, label='node')
        node.shell(user=user)

if __name__ == "__main__":
    from starcluster.config import StarClusterConfig
    cfg = StarClusterConfig().load()
    sc = cfg.get_cluster_template('smallcluster', 'mynewcluster')
    if sc.is_valid():
        sc.start(create=True)
