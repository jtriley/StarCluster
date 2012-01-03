import os
import re
import time
import zlib
import string
import pprint
import base64
import cPickle
import traceback

from starcluster import ssh
from starcluster import utils
from starcluster import static
from starcluster import spinner
from starcluster import iptools
from starcluster import managers
from starcluster import exception
from starcluster import progressbar
from starcluster import clustersetup
from starcluster.node import Node
from starcluster.utils import print_timing
from starcluster.templates import user_msgs
from starcluster.logger import log


class ClusterManager(managers.Manager):
    """
    Manager class for Cluster objects
    """
    def __repr__(self):
        return "<ClusterManager: %s>" % self.ec2.region.name

    def get_cluster(self, cluster_name, group=None, load_receipt=True,
                    load_plugins=True, require_keys=True):
        """
        Returns a Cluster object representing an active cluster
        """
        try:
            clname = self._get_cluster_name(cluster_name)
            cltag = self.get_tag_from_sg(clname)
            if not group:
                group = self.ec2.get_security_group(clname)
            cl = Cluster(ec2_conn=self.ec2, cluster_tag=cltag,
                         cluster_group=group)
            if load_receipt:
                cl.load_receipt(load_plugins=load_plugins)
            try:
                key_location = self.cfg.get_key(cl.keyname).get('key_location')
                cl.key_location = key_location
            except exception.KeyNotFound:
                if require_keys:
                    raise
                cl.key_location = ''
            if require_keys:
                cl._validate_keypair()
            return cl
        except exception.SecurityGroupDoesNotExist:
            raise exception.ClusterDoesNotExist(cluster_name)

    def get_clusters(self, load_receipt=True, load_plugins=True):
        """
        Returns a list of all active clusters
        """
        cluster_groups = self.get_cluster_security_groups()
        clusters = [self.get_cluster(g.name, group=g,
                                     load_receipt=load_receipt,
                                     load_plugins=load_plugins)
                    for g in cluster_groups]
        return clusters

    def get_default_cluster_template(self):
        """
        Returns name of the default cluster template defined in the config
        """
        return self.cfg.get_default_cluster_template()

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

    def get_cluster_or_none(self, cluster_name, **kwargs):
        """
        Same as get_cluster but returns None instead of throwing an exception
        if the cluster does not exist
        """
        try:
            return self.get_cluster(cluster_name, **kwargs)
        except exception.ClusterDoesNotExist:
            pass

    def cluster_exists(self, tag_name):
        """
        Returns True if cluster exists
        """
        return self.get_cluster_or_none(tag_name) is not None

    def ssh_to_master(self, cluster_name, user='root', command=None):
        """
        ssh to master node of cluster_name

        user keyword specifies an alternate user to login as
        """
        cluster = self.get_cluster(cluster_name)
        return cluster.ssh_to_master(user=user, command=command)

    def ssh_to_cluster_node(self, cluster_name, node_id, user='root',
                            command=None):
        """
        ssh to a node in cluster_name that has either an id,
        dns name, or alias matching node_id

        user keyword specifies an alternate user to login as
        """
        cluster = self.get_cluster(cluster_name)
        return cluster.ssh_to_node(node_id, user=user, command=command)

    def _get_cluster_name(self, cluster_name):
        """
        Returns human readable cluster name/tag prefixed with '@sc-'
        """
        if not cluster_name.startswith(static.SECURITY_GROUP_PREFIX):
            cluster_name = static.SECURITY_GROUP_TEMPLATE % cluster_name
        return cluster_name

    def add_node(self, cluster_name, alias=None, no_create=False):
        cl = self.get_cluster(cluster_name)
        cl.add_node(alias, no_create=no_create)

    def add_nodes(self, cluster_name, num_nodes, aliases=None,
                  no_create=False):
        """
        Add one or more nodes to cluster
        """
        cl = self.get_cluster(cluster_name)
        cl.add_nodes(num_nodes, aliases=aliases, no_create=no_create)

    def remove_node(self, cluster_name, alias, terminate=True):
        """
        Remove a single node from a cluster
        """
        cl = self.get_cluster(cluster_name)
        n = cl.get_node_by_alias(alias)
        if not n:
            raise exception.InstanceDoesNotExist(alias, label='node')
        cl.remove_node(n, terminate=terminate)

    def restart_cluster(self, cluster_name):
        """
        Reboots and reconfigures cluster_name
        """
        cl = self.get_cluster(cluster_name)
        cl.restart_cluster()

    def stop_cluster(self, cluster_name, terminate_unstoppable=False):
        """
        Stop an EBS-backed cluster
        """
        cl = self.get_cluster(cluster_name, require_keys=False)
        cl.stop_cluster(terminate_unstoppable)

    def terminate_cluster(self, cluster_name):
        """
        Terminates cluster_name
        """
        cl = self.get_cluster(cluster_name, require_keys=False)
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

    def list_clusters(self, cluster_groups=None, show_ssh_status=False):
        """
        Prints a summary for each active cluster on EC2
        """
        if not cluster_groups:
            cluster_groups = self.get_cluster_security_groups()
            if not cluster_groups:
                log.info("No clusters found...")
        else:
            try:
                cluster_groups = [self.get_cluster_security_group(g) for g
                                  in cluster_groups]
            except exception.SecurityGroupDoesNotExist:
                raise exception.ClusterDoesNotExist(g)
        for scg in cluster_groups:
            tag = self.get_tag_from_sg(scg.name)
            try:
                cl = self.get_cluster(tag, group=scg, load_plugins=False,
                                      require_keys=False)
            except exception.IncompatibleCluster, e:
                sep = '*' * 60
                log.error('\n'.join([sep, e.msg, sep]),
                          extra=dict(__textwrap__=True))
                continue
            header = '%s (security group: %s)' % (tag, scg.name)
            print '-' * len(header)
            print header
            print '-' * len(header)
            nodes = cl.nodes
            try:
                n = nodes[0]
            except IndexError:
                n = None
            state = getattr(n, 'state', None)
            ltime = 'N/A'
            uptime = 'N/A'
            if state in ['pending', 'running']:
                ltime = getattr(n, 'local_launch_time', 'N/A')
                uptime = getattr(n, 'uptime', 'N/A')
            print 'Launch time: %s' % ltime
            print 'Uptime: %s' % uptime
            print 'Zone: %s' % getattr(n, 'placement', 'N/A')
            print 'Keypair: %s' % getattr(n, 'key_name', 'N/A')
            ebs_nodes = [n for n in nodes if n.attached_vols]
            if ebs_nodes:
                print 'EBS volumes:'
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
                print 'EBS volumes: N/A'
            spot_reqs = cl.spot_requests
            if spot_reqs:
                active = len([s for s in spot_reqs if s.state == 'active'])
                opn = len([s for s in spot_reqs if s.state == 'open'])
                msg = ''
                if active != 0:
                    msg += '%d active' % active
                if opn != 0:
                    if msg:
                        msg += ', '
                    msg += '%d open' % opn
                print 'Spot requests: %s' % msg
            if nodes:
                print 'Cluster nodes:'
                for node in nodes:
                    nodeline = "    %7s %s %s %s" % (node.alias, node.state,
                                                        node.id, node.dns_name)
                    if node.spot_id:
                        nodeline += ' (spot %s)' % node.spot_id
                    if show_ssh_status:
                        ssh_status = {True: 'Up', False: 'Down'}
                        nodeline += ' (SSH: %s)' % ssh_status[node.is_up()]
                    print nodeline
                print 'Total nodes: %d' % len(nodes)
            else:
                print 'Cluster nodes: N/A'
            print

    def run_plugin(self, plugin_name, cluster_tag):
        """
        Run a plugin defined in the config.

        plugin_name must match the plugin's section name in the config
        cluster_tag specifies the cluster to run the plugin on
        """
        cl = self.get_cluster(cluster_tag, load_plugins=False)
        if not cl.is_cluster_up():
            raise exception.ClusterNotRunning(cluster_tag)
        plugs = [self.cfg.get_plugin(plugin_name)]
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
            refresh_interval=30,
            disable_queue=False,
            disable_threads=False,
            cluster_group=None,
            force_spot_master=False,
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
        self.refresh_interval = refresh_interval
        self.disable_queue = disable_queue
        self.disable_threads = disable_threads
        self.force_spot_master = force_spot_master

        self.__instance_types = static.INSTANCE_TYPES
        self.__cluster_settings = static.CLUSTER_SETTINGS
        self.__available_shells = static.AVAILABLE_SHELLS
        self.__protocols = static.PROTOCOLS
        self._progress_bar = None
        self._master_reservation = None
        self._node_reservation = None
        self._nodes = []
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
        volumes are not in the same availability zone an exception is raised.
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
        etc. for all volumes that do not include a device/partition setting
        """
        devices = ['/dev/sd%s' % s for s in string.lowercase]
        devmap = {}
        for volname in vols:
            vol = vols.get(volname)
            dev = vol.get('device')
            if dev in devices:
                #rm user-defined devices from the list of auto-assigned devices
                devices.remove(dev)
            volid = vol.get('volume_id')
            if dev and not volid in devmap:
                devmap[volid] = dev
        volumes = {}
        for volname in vols:
            vol = vols.get(volname)
            vol_id = vol.get('volume_id')
            device = vol.get('device')
            if not device:
                if vol_id in devmap:
                    device = devmap.get(vol_id)
                else:
                    device = devices.pop()
                    devmap[vol_id] = device
            if not utils.is_valid_device(device):
                raise exception.InvalidDevice(device)
            v = volumes[volname] = utils.AttributeDict()
            v.update(vol)
            v['device'] = device
            part = vol.get('partition')
            if part:
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
                    "Plugin %s (%s) contains a syntax error at line %s" %
                    (plugin_name, e.filename, e.lineno))
            except ImportError, e:
                raise exception.PluginLoadError(
                    "Failed to import plugin %s: %s" %
                    (plugin_name, e[0]))
            klass = getattr(mod, class_name, None)
            if not klass:
                raise exception.PluginError(
                    'Plugin class %s does not exist' % setup_class)
            if not issubclass(klass, clustersetup.ClusterSetup):
                raise exception.PluginError(
                    "Plugin %s must be a subclass of "
                    "starcluster.clustersetup.ClusterSetup" % setup_class)
            args, kwargs = utils.get_arg_spec(klass.__init__)
            config_args = []
            missing_args = []
            for arg in args:
                if arg in plugin:
                    config_args.append(plugin.get(arg))
                else:
                    missing_args.append(arg)
            log.debug("config_args = %s" % config_args)
            if missing_args:
                raise exception.PluginError(
                    "Not enough settings provided for plugin %s (missing: %s)"
                    % (plugin_name, ', '.join(missing_args)))
            config_kwargs = {}
            for arg in kwargs:
                if arg in plugin:
                    config_kwargs[arg] = plugin.get(arg)
            log.debug("config_kwargs = %s" % config_kwargs)
            plugs.append((plugin_name, klass(*config_args, **config_kwargs)))
        return plugs

    def update(self, kwargs):
        for key in kwargs.keys():
            if hasattr(self, key):
                self.__dict__[key] = kwargs[key]

    def _validate_running_instances(self):
        """
        Validate existing instances against this cluster's settings
        """
        self.wait_for_active_spots()
        nodes = self.nodes
        if not nodes:
            raise exception.ClusterValidationError("No existing nodes found!")
        log.info("Validating existing instances...")
        mazone = self.master_node.placement
        rlmap = self._get_launch_map(reverse=True)
        for node in nodes:
            itype, image = rlmap.get(node.alias)
            alias = node.alias
            ntype = node.instance_type
            if ntype != itype:
                raise exception.ClusterValidationError(
                    "%s's instance type (%s) != %s" % (alias, ntype, itype))
            nimage = node.image_id
            if nimage != image:
                raise exception.ClusterValidationError(
                    "%s's image id (%s) != %s" % (alias, nimage, image))
            if node.key_name != self.keyname:
                raise exception.ClusterValidationError(
                    "%s's key_name (%s) != %s" % (alias, node.key_name,
                                                  self.keyname))
            nazone = node.placement
            if mazone != nazone:
                raise exception.ClusterValidationError(
                    "Node '%s' zone (%s) does not match master's zone (%s)" %
                    (alias, nazone, mazone))
        # reset zone cache
        self._zone = None
        if self.zone and self.zone != mazone:
            raise exception.ClusterValidationError(
                "Running cluster's availability_zone (%s) != %s" %
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
            desc = self.cluster_group.description
            version, b64data = desc.split('-', 1)
            if utils.program_version_greater(version, static.VERSION):
                d = dict(cluster=self.cluster_tag, old_version=static.VERSION,
                         new_version=version)
                msg = user_msgs.version_mismatch % d
                sep = '*' * 60
                log.warn('\n'.join([sep, msg, sep]), extra={'__textwrap__': 1})
            compressed_data = base64.b64decode(b64data)
            pkl_data = zlib.decompress(compressed_data)
            cluster_settings = cPickle.loads(str(pkl_data)).__dict__
        except (cPickle.PickleError, zlib.error, ValueError, TypeError,
                EOFError, IndexError), e:
            log.debug('load receipt exception: ', exc_info=True)
            raise exception.IncompatibleCluster(self.cluster_group)
        except Exception, e:
            raise exception.ClusterReceiptError(
                'failed to load cluster receipt: %s' % e)
        for key in cluster_settings:
            if hasattr(self, key):
                setattr(self, key, cluster_settings.get(key))
        if load_plugins:
            try:
                self.plugins = self.load_plugins(self._plugins)
            except exception.PluginError, e:
                log.warn(e)
                log.warn("An error occurred while loading plugins")
                log.warn("Not running any plugins")
            except Exception, e:
                raise exception.ClusterReceiptError(
                    'failed to load cluster receipt: %s' % e)
        return True

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
            ssh_port = static.DEFAULT_SSH_PORT
            desc = base64.b64encode(zlib.compress(cPickle.dumps(self)))
            desc = '-'.join([static.VERSION, desc])
            sg = self.ec2.get_or_create_group(self._security_group,
                                              desc,
                                              auth_ssh=True,
                                              auth_group_traffic=True)
            for p in self.permissions:
                perm = self.permissions.get(p)
                ip_protocol = perm.get('ip_protocol', 'tcp')
                from_port = perm.get('from_port')
                to_port = perm.get('to_port')
                cidr_ip = perm.get('cidr_ip', static.WORLD_CIDRIP)
                if not self.ec2.has_permission(sg, ip_protocol, from_port,
                                               to_port, cidr_ip):
                    log.info("Opening %s port range %s-%s for CIDR %s" %
                             (ip_protocol, from_port, to_port, cidr_ip))
                    sg.authorize(ip_protocol, from_port, to_port, cidr_ip)
                if ip_protocol == 'tcp' and from_port <= ssh_port <= to_port:
                    sg.revoke(ip_protocol, ssh_port, ssh_port,
                              static.WORLD_CIDRIP)
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
            if not self._master:
                raise exception.MasterDoesNotExist()
        return self._master

    @property
    def nodes(self):
        states = ['pending', 'running', 'stopping', 'stopped']
        filters = {'group-name': self._security_group,
                   'instance-state-name': states}
        nodes = self.ec2.get_all_instances(filters=filters)
        # remove any cached nodes not in the current node list from EC2
        current_ids = [n.id for n in nodes]
        remove_nodes = [n for n in self._nodes if n.id not in current_ids]
        for node in remove_nodes:
            self._nodes.remove(node)
        # update node cache with latest instance data from EC2
        existing_nodes = dict([(n.id, n) for n in self._nodes])
        log.debug('existing nodes: %s' % existing_nodes)
        for node in nodes:
            if node.id in existing_nodes:
                log.debug('updating existing node %s in self._nodes' % node.id)
                enode = existing_nodes.get(node.id)
                enode.key_location = self.key_location
                enode.instance = node
            else:
                log.debug('adding node %s to self._nodes list' % node.id)
                n = Node(node, self.key_location)
                if n.is_master():
                    self._master = n
                    self._nodes.insert(0, n)
                else:
                    self._nodes.append(n)
        self._nodes.sort(key=lambda n: n.alias)
        log.debug('returning self._nodes = %s' % self._nodes)
        return self._nodes

    def get_nodes_or_raise(self):
        nodes = self.nodes
        if not nodes:
            filters = {'group-name': self._security_group}
            terminated_nodes = self.ec2.get_all_instances(filters=filters)
            raise exception.NoClusterNodesFound(terminated_nodes)
        return nodes

    def get_node_by_dns_name(self, dns_name):
        for node in self.nodes:
            if node.dns_name == dns_name:
                return node
        raise exception.InstanceDoesNotExist(dns_name, label='node')

    def get_node_by_id(self, instance_id):
        for node in self.nodes:
            if node.id == instance_id:
                return node
        raise exception.InstanceDoesNotExist(instance_id, label='node')

    def get_node_by_alias(self, alias):
        for node in self.nodes:
            if node.alias == alias:
                return node
        raise exception.InstanceDoesNotExist(alias, label='node')

    def _nodes_in_states(self, states):
        return filter(lambda x: x.state in states, self.nodes)

    @property
    def running_nodes(self):
        return self._nodes_in_states(['running'])

    @property
    def stopped_nodes(self):
        return self._nodes_in_states(['stopping', 'stopped'])

    @property
    def spot_requests(self):
        filters = {'launch.group-id': self.cluster_group.id,
                   'state': ['active', 'open']}
        return self.ec2.get_all_spot_requests(filters=filters)

    def get_spot_requests_or_raise(self):
        spots = self.spot_requests
        if not spots:
            raise exception.NoClusterSpotRequests
        return spots

    def create_node(self, alias, image_id=None, instance_type=None, zone=None,
                    placement_group=None, spot_bid=None, force_flat=False):
        return self.create_nodes([alias], image_id=image_id,
                                 instance_type=instance_type, zone=zone,
                                 placement_group=placement_group,
                                 spot_bid=spot_bid, force_flat=force_flat)[0]

    def create_nodes(self, aliases, image_id=None, instance_type=None,
                     zone=None, placement_group=None, spot_bid=None,
                     force_flat=False):
        """
        Convenience method for requesting instances with this cluster's
        settings. All settings (kwargs) except force_flat default to cluster
        settings if not provided. Passing force_flat=True ignores spot_bid
        completely forcing a flat-rate instance to be requested.
        """
        spot_bid = spot_bid or self.spot_bid
        if force_flat:
            spot_bid = None
        cluster_sg = self.cluster_group.name
        instance_type = instance_type or self.node_instance_type
        if not placement_group and instance_type in static.CLUSTER_TYPES:
            placement_group = self.placement_group.name
        image_id = image_id or self.node_image_id
        count = len(aliases) if not spot_bid else 1
        kwargs = dict(price=spot_bid, instance_type=instance_type,
                      min_count=count, max_count=count, count=count,
                      key_name=self.keyname, security_groups=[cluster_sg],
                      availability_zone_group=cluster_sg,
                      launch_group=cluster_sg, placement=zone or self.zone,
                      user_data='|'.join(aliases),
                      placement_group=placement_group)
        resvs = []
        if spot_bid:
            for alias in aliases:
                kwargs['user_data'] = alias
                resvs.extend(self.ec2.request_instances(image_id, **kwargs))
        else:
            resvs.append(self.ec2.request_instances(image_id, **kwargs))
        for resv in resvs:
            log.info(str(resv), extra=dict(__raw__=True))
        return resvs

    def _get_next_node_num(self):
        nodes = self._nodes_in_states(['pending', 'running'])
        nodes = filter(lambda x: not x.is_master(), nodes)
        highest = 0
        for n in nodes:
            try:
                highest = max(highest, int(n.alias[4:8]))
            except ValueError:
                pass
        next = highest + 1
        log.debug("Highest node number is %d. choosing %d." % (highest, next))
        return next

    def add_node(self, alias=None, no_create=False):
        """
        Add a single node to this cluster
        """
        aliases = None
        if alias:
            aliases = [alias]
        self.add_nodes(1, aliases=aliases, no_create=no_create)

    def add_nodes(self, num_nodes, aliases=None, no_create=False):
        """
        Add new nodes to this cluster

        aliases - list of aliases to assign to new nodes (len must equal
        num_nodes)
        """
        running_pending = self._nodes_in_states(['pending', 'running'])
        aliases = aliases or []
        if not aliases:
            next_node_id = self._get_next_node_num()
            for i in range(next_node_id, next_node_id + num_nodes):
                alias = 'node%.3d' % i
                aliases.append(alias)
        assert len(aliases) == num_nodes
        if "master" in aliases:
            raise exception.ClusterValidationError(
                "worker nodes cannot have master as an alias")
        if not no_create:
            for node in running_pending:
                if node.alias in aliases:
                    raise exception.ClusterValidationError(
                        "node with alias %s already exists" % node.alias)
            log.info("Launching node(s): %s" % ', '.join(aliases))
            self.create_nodes(aliases)
        self.wait_for_cluster(msg="Waiting for node(s) to come up...")
        log.debug("Adding node(s): %s" % aliases)
        default_plugin = clustersetup.DefaultClusterSetup(self.disable_queue,
                                                          self.disable_threads)
        for alias in aliases:
            node = self.get_node_by_alias(alias)
            default_plugin.on_add_node(
                node, self.nodes, self.master_node,
                self.cluster_user, self.cluster_shell,
                self.volumes)
            self.run_plugins(method_name="on_add_node", node=node)

    def remove_node(self, node, terminate=True):
        """
        Remove a single node from this cluster
        """
        return self.remove_nodes([node], terminate=terminate)

    def remove_nodes(self, nodes, terminate=True):
        """
        Remove a list of nodes from this cluster
        """
        default_plugin = clustersetup.DefaultClusterSetup(self.disable_queue,
                                                          self.disable_threads)
        for node in nodes:
            if node.is_master():
                raise exception.InvalidOperation("cannot remove master node")
            self.run_plugins(method_name="on_remove_node",
                             node=node, reverse=True)
            default_plugin.on_remove_node(
                node, self.nodes, self.master_node,
                self.cluster_user, self.cluster_shell,
                self.volumes)
            if not terminate:
                continue
            if node.spot_id:
                log.info("Canceling spot request %s" % node.spot_id)
                node.get_spot_request().cancel()
            node.terminate()

    def _get_launch_map(self, reverse=False):
        """
        Groups all node-aliases that have similar instance types/image ids
        Returns a dictionary that's used to launch all similar instance types
        and image ids in the same request. Example return value:

        {('c1.xlarge', 'ami-a5c02dcc'): ['node001', 'node002'],
         ('m1.large', 'ami-a5c02dcc'): ['node003'],
         ('m1.small', 'ami-17b15e7e'): ['master', 'node005', 'node006'],
         ('m1.small', 'ami-19e17a2b'): ['node004']}

        Passing reverse=True will return the same information only keyed by
        node aliases:

        {'master': ('m1.small', 'ami-17b15e7e'),
         'node001': ('c1.xlarge', 'ami-a5c02dcc'),
         'node002': ('c1.xlarge', 'ami-a5c02dcc'),
         'node003': ('m1.large', 'ami-a5c02dcc'),
         'node004': ('m1.small', 'ami-19e17a2b'),
         'node005': ('m1.small', 'ami-17b15e7e'),
         'node006': ('m1.small', 'ami-17b15e7e')}
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
                log.debug("Launch map: %s (ami: %s, type: %s)..." %
                          (alias, image_id, type))
                lmap[(type, image_id)].append(alias)
                id_start += 1
        ntype = self.node_instance_type
        nimage = self.node_image_id
        if not (ntype, nimage) in lmap:
            lmap[(ntype, nimage)] = []
        for id in range(id_start, self.cluster_size):
            alias = 'node%.3d' % id
            log.debug("Launch map: %s (ami: %s, type: %s)..." %
                      (alias, nimage, ntype))
            lmap[(ntype, nimage)].append(alias)
        if reverse:
            rlmap = {}
            for (itype, image_id) in lmap:
                aliases = lmap.get((itype, image_id))
                for alias in aliases:
                    rlmap[alias] = (itype, image_id)
            return rlmap
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

    def create_cluster(self):
        """
        Launches all EC2 instances based on this cluster's settings.
        """
        log.info("Launching a %d-node cluster..." % self.cluster_size)
        mtype = self.master_instance_type or self.node_instance_type
        self.master_instance_type = mtype
        if self.spot_bid:
            self._create_spot_cluster()
        else:
            self._create_flat_rate_cluster()

    def _create_flat_rate_cluster(self):
        """
        Launches cluster using flat-rate instances. This method attempts to
        minimize the number of launch requests by grouping nodes of the same
        type/ami and launching each group simultaneously within a single launch
        request. This is especially important for Cluster Compute instances
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
                for alias in aliases:
                    log.debug("Launching %s (ami: %s, type: %s)" %
                              (alias, image, type))
                master_response = self.create_nodes(aliases, image_id=image,
                                                    instance_type=type,
                                                    force_flat=True)[0]
                zone = master_response.instances[0].placement
        lmap.pop(master_map)
        if self.cluster_size <= 1:
            return
        for (type, image) in lmap:
            aliases = lmap.get((type, image))
            for alias in aliases:
                log.debug("Launching %s (ami: %s, type: %s)" %
                          (alias, image, type))
            self.create_nodes(aliases, image_id=image, instance_type=type,
                              zone=zone, force_flat=True)

    def _create_spot_cluster(self):
        """
        Launches cluster using all spot instances. This method makes a single
        spot request for each node in the cluster since spot instances
        *always* have an ami_launch_index of 0. This is needed in order to
        correctly assign aliases to nodes.
        """
        (mtype, mimage) = self._get_type_and_image_id('master')
        log.info("Launching master node (ami: %s, type: %s)..." %
                 (mimage, mtype))
        force_flat = not self.force_spot_master and self.cluster_size > 1
        master_response = self.create_node('master',
                                           image_id=mimage,
                                           instance_type=mtype,
                                           force_flat=force_flat)
        zone = None
        if not force_flat and self.spot_bid:
            # Make sure nodes are in same zone as master
            launch_spec = master_response.launch_specification
            zone = launch_spec.placement
        else:
            # Make sure nodes are in same zone as master
            zone = master_response.instances[0].placement
        if self.cluster_size <= 1:
            return
        for id in range(1, self.cluster_size):
            alias = 'node%.3d' % id
            (ntype, nimage) = self._get_type_and_image_id(alias)
            log.info("Launching %s (ami: %s, type: %s)" %
                     (alias, nimage, ntype))
            self.create_node(alias, image_id=nimage, instance_type=ntype,
                             zone=zone)

    def is_spot_cluster(self):
        """
        Returns True if all nodes are spot instances
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if not node.is_spot():
                return False
        return True

    def has_spot_nodes(self):
        """
        Returns True if any nodes are spot instances
        """
        for node in self.nodes:
            if node.is_spot():
                return True
        return False

    def is_ebs_cluster(self):
        """
        Returns True if all nodes are EBS-backed
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if not node.is_ebs_backed():
                return False
        return True

    def has_ebs_nodes(self):
        """
        Returns True if any nodes are EBS-backed
        """
        for node in self.nodes:
            if node.is_ebs_backed():
                return True
        return False

    def is_stoppable(self):
        """
        Returns True if all nodes are stoppable (i.e. non-spot and EBS-backed)
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in self.nodes:
            if not node.is_stoppable():
                return False
        return True

    def has_stoppable_nodes(self):
        """
        Returns True if any nodes are stoppable (i.e. non-spot and EBS-backed)
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if node.is_stoppable():
                return True
        return False

    def is_cluster_compute(self):
        """
        Returns true if all instances are Cluster/GPU Compute type
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if not node.is_cluster_compute():
                return False
        return True

    def has_cluster_compute_nodes(self):
        for node in self.nodes:
            if node.is_cluster_compute():
                return True
        return False

    def is_cluster_up(self):
        """
        Check that all nodes are 'running' and that ssh is up on all nodes
        This method will return False if any spot requests are in an 'open'
        state.
        """
        spots = self.spot_requests
        active_spots = filter(lambda x: x.state == 'active', spots)
        if len(spots) != len(active_spots):
            return False
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if not node.is_up():
                return False
        return True

    def get_spinner(self, msg):
        """
        Logs a status msg, starts a spinner, and returns the spinner object.
        This is useful for long running processes:

            s = self.get_spinner("Long running process running...")
            (do something)
            s.stop()
        """
        s = spinner.Spinner()
        log.info(msg, extra=dict(__nonewline__=True))
        s.start()
        return s

    @property
    def progress_bar(self):
        if not self._progress_bar:
            widgets = ['', progressbar.Fraction(), ' ',
                       progressbar.Bar(marker=progressbar.RotatingMarker()),
                       ' ', progressbar.Percentage(), ' ', ' ']
            pbar = progressbar.ProgressBar(widgets=widgets,
                                           maxval=self.cluster_size,
                                           force_update=True)
            self._progress_bar = pbar
        return self._progress_bar

    def wait_for_active_spots(self, spots=None):
        """
        Wait for all open spot requests for this cluster to transition to
        'active'.
        """
        spots = spots or self.spot_requests
        open_spots = [spot for spot in spots if spot.state == "open"]
        if open_spots:
            pbar = self.progress_bar.reset()
            log.info('Waiting for open spot requests to become active...')
            pbar.maxval = len(spots)
            pbar.update(0)
            while not pbar.finished:
                active_spots = filter(lambda x: x.state == "active", spots)
                pbar.maxval = len(spots)
                pbar.update(len(active_spots))
                if not pbar.finished:
                    time.sleep(self.refresh_interval)
                    spots = self.get_spot_requests_or_raise()
            pbar.reset()

    def wait_for_active_instances(self, nodes=None):
        """
        Wait indefinitely for cluster nodes to show up.
        """
        nodes = nodes or self.nodes
        if len(nodes) == 0:
            s = self.get_spinner("Waiting for instances to activate...")
            while len(nodes) == 0:
                time.sleep(self.refresh_interval)
                nodes = self.nodes
            s.stop()

    def wait_for_running_instances(self, nodes=None):
        """
        Wait until all cluster nodes are in a 'running' state
        """
        log.info("Waiting for all nodes to be in a 'running' state...")
        nodes = nodes or self.get_nodes_or_raise()
        pbar = self.progress_bar.reset()
        pbar.maxval = len(nodes)
        pbar.update(0)
        while not pbar.finished:
            running_nodes = filter(lambda x: x.state == "running", nodes)
            pbar.maxval = len(nodes)
            pbar.update(len(running_nodes))
            if not pbar.finished:
                time.sleep(self.refresh_interval)
                nodes = self.get_nodes_or_raise()
        pbar.reset()

    def wait_for_ssh(self, nodes=None):
        """
        Wait until all cluster nodes are in a 'running' state
        """
        log.info("Waiting for SSH to come up on all nodes...")
        nodes = nodes or self.get_nodes_or_raise()
        pbar = self.progress_bar.reset()
        pbar.maxval = len(nodes)
        pbar.update(0)
        while not pbar.finished:
            active_nodes = filter(lambda n: n.is_up(), nodes)
            pbar.maxval = len(nodes)
            pbar.update(len(active_nodes))
            if not pbar.finished:
                time.sleep(self.refresh_interval)
                nodes = self.get_nodes_or_raise()
        pbar.finish()

    @print_timing("Waiting for cluster to come up")
    def wait_for_cluster(self, msg="Waiting for cluster to come up..."):
        """
        Wait for cluster to come up and display progress bar. Waits for all
        spot requests to become 'active', all instances to be in a 'running'
        state, and for all SSH daemons to come up.

        msg - custom message to print out before waiting on the cluster
        """
        interval = self.refresh_interval
        log.info("%s %s" % (msg, "(updating every %ds)" % interval))
        self.wait_for_active_spots()
        self.wait_for_active_instances()
        self.wait_for_running_instances()
        self.wait_for_ssh()

    def is_cluster_stopped(self):
        """
        Check whether all nodes are in the 'stopped' state
        """
        nodes = self.nodes
        if not nodes:
            return False
        for node in nodes:
            if node.state != 'stopped':
                return False
        return True

    def is_cluster_terminated(self):
        """
        Check whether all nodes are in a 'terminated' state
        """
        states = filter(lambda x: x != 'terminated', static.INSTANCE_STATES)
        filters = {'group-name': self._security_group,
                   'instance-state-name': states}
        insts = self.ec2.get_all_instances(filters=filters)
        return len(insts) == 0

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
                log.info("Volume %s already attached to master...skipping" %
                         vol.id)
                continue
            if vol.status != "available":
                log.error('Volume %s not available...'
                          'please check and try again' % vol.id)
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
        Detach all volumes from all nodes
        """
        for node in self.nodes:
            node.detach_external_volumes()

    @print_timing('Restarting cluster')
    def restart_cluster(self):
        """
        Reboot all instances and reconfigure the cluster
        """
        nodes = self.nodes
        if not nodes:
            raise exception.ClusterValidationError("No running nodes found")
        self.run_plugins(method_name="on_restart", reverse=True)
        log.info("Rebooting cluster...")
        for node in nodes:
            node.reboot()
        sleep = 20
        log.info("Sleeping for %d seconds..." % sleep)
        time.sleep(sleep)
        self.setup_cluster()

    def stop_cluster(self, terminate_unstoppable=False):
        """
        Shutdown this cluster by detaching all volumes and 'stopping' all nodes

        In general, all nodes in the cluster must be 'stoppable' meaning all
        nodes are backed by flat-rate EBS-backed instances. If any
        'unstoppable' nodes are found an exception is raised. A node is
        'unstoppable' if it is backed by either a spot or S3-backed instance.

        If the cluster contains a mix of 'stoppable' and 'unstoppable' nodes
        you can stop all stoppable nodes and terminate any unstoppable nodes by
        setting terminate_unstoppable=True.

        This will stop all nodes that can be stopped and terminate the rest.
        """
        nodes = self.nodes
        if not nodes:
            raise exception.ClusterValidationError("No running nodes found")
        if not self.is_stoppable():
            has_stoppable_nodes = self.has_stoppable_nodes()
            if not terminate_unstoppable and has_stoppable_nodes:
                raise exception.InvalidOperation(
                    "Cluster contains nodes that are not stoppable")
            if not has_stoppable_nodes:
                raise exception.InvalidOperation(
                    "Cluster does not contain any stoppable nodes")
        try:
            self.run_plugins(method_name="on_shutdown", reverse=True)
        except exception.MasterDoesNotExist, e:
            log.warn("Cannot run plugins: %s" % e)
        self.detach_volumes()
        for node in nodes:
            node.shutdown()

    def terminate_cluster(self):
        """
        Destroy this cluster by first detaching all volumes, shutting down all
        instances, canceling all spot requests (if any), removing its placement
        group (if any), and removing its security group.
        """
        try:
            self.run_plugins(method_name="on_shutdown", reverse=True)
        except exception.MasterDoesNotExist, e:
            log.warn("Cannot run plugins: %s" % e)
        self.detach_volumes()
        nodes = self.nodes
        for node in nodes:
            node.terminate()
        for spot in self.spot_requests:
            if spot.state not in ['cancelled', 'closed']:
                log.info("Canceling spot instance request: %s" % spot.id)
                spot.cancel()
        sg = self.ec2.get_group_or_none(self._security_group)
        pg = self.ec2.get_placement_group_or_none(self._security_group)
        s = self.get_spinner("Waiting for cluster to terminate...")
        while not self.is_cluster_terminated():
            time.sleep(5)
        s.stop()
        if pg:
            log.info("Removing %s placement group" % pg.name)
            pg.delete()
        if sg:
            log.info("Removing %s security group" % sg.name)
            sg.delete()

    def start(self, create=True, create_only=False, validate=True,
              validate_only=False, validate_running=False):
        """
        Creates and configures a cluster from this cluster template's settings.

        create - create new nodes when starting the cluster. set to False to
                 use existing nodes
        create_only - only create the cluster node instances, don't configure
                      the cluster
        validate - whether or not to validate the cluster settings used.
                   False will ignore validate_only and validate_running
                   keywords and is effectively the same as running _start
        validate_only - only validate cluster settings, do not create or
                        configure cluster
        validate_running - whether or not to validate the existing instances
                           being used against this cluster's settings
        """
        if validate:
            if not create and validate_running:
                try:
                    self._validate_running_instances()
                except exception.ClusterValidationError, e:
                    msg = "Existing nodes are not compatible with cluster "
                    msg += "settings:\n"
                    e.msg = msg + e.msg
                    raise
            self._validate()
            if validate_only:
                return
        else:
            log.warn("SKIPPING VALIDATION - USE AT YOUR OWN RISK")
        return self._start(create=create, create_only=create_only)

    @print_timing("Starting cluster")
    def _start(self, create=True, create_only=False):
        """
        Create and configure a cluster from this cluster template's settings
        (Does not attempt to validate before running)

        create - create new nodes when starting the cluster. set to False to
                 use existing nodes
        create_only - only create the cluster node instances, don't configure
                      the cluster
        """
        log.info("Starting cluster...")
        if create:
            self.create_cluster()
        else:
            assert self.master_node is not None
            for node in self.stopped_nodes:
                log.info("Starting stopped node: %s" % node.alias)
                node.start()
        if create_only:
            return
        self.setup_cluster()

    def setup_cluster(self):
        """
        Waits for all nodes to come up and then runs the default
        StarCluster setup routines followed by any additional plugin setup
        routines
        """
        self.wait_for_cluster()
        self._setup_cluster()

    @print_timing("Configuring cluster")
    def _setup_cluster(self):
        """
        Runs the default StarCluster setup routines followed by any additional
        plugin setup routines. Does not wait for nodes to come up.
        """
        log.info("The master node is %s" % self.master_node.dns_name)
        log.info("Setting up the cluster...")
        if self.volumes:
            self.attach_volumes_to_master()
        default_plugin = clustersetup.DefaultClusterSetup(self.disable_queue,
                                                          self.disable_threads)
        default_plugin.run(self.nodes, self.master_node, self.cluster_user,
                           self.cluster_shell, self.volumes)
        self.run_plugins()

    def run_plugins(self, plugins=None, method_name="run", node=None,
                    reverse=False):
        """
        Run all plugins specified in this Cluster object's self.plugins list
        Uses plugins list instead of self.plugins if specified.

        plugins must be a tuple: the first element is the plugin's name, the
        second element is the plugin object (a subclass of ClusterSetup)
        """
        plugs = plugins or self.plugins
        if reverse:
            plugs = plugs[:]
            plugs.reverse()
        for plug in plugs:
            name, plugin = plug
            self.run_plugin(plugin, name, method_name=method_name, node=node)

    def run_plugin(self, plugin, name='', method_name='run', node=None):
        """
        Run a StarCluster plugin.

        plugin - an instance of the plugin's class
        name - a user-friendly label for the plugin
        method_name - the method to run within the plugin (default: "run")
        node - optional node to pass as first argument to plugin method (used
        for on_add_node/on_remove_node)
        """
        plugin_name = name or str(plugin)
        try:
            func = getattr(plugin, method_name, None)
            if not func:
                log.warn("Plugin %s has no %s method...skipping" %
                         (plugin_name, method_name))
                return
            args = [self.nodes, self.master_node, self.cluster_user,
                    self.cluster_shell, self.volumes]
            if node:
                args.insert(0, node)
            log.info("Running plugin %s" % plugin_name)
            func(*args)
        except NotImplementedError:
            log.debug("method %s not implemented by plugin %s" % (method_name,
                                                                  plugin_name))
        except exception.MasterDoesNotExist:
            raise
        except Exception, e:
            log.error("Error occurred while running plugin '%s':" %
                      plugin_name)
            if isinstance(e, exception.ThreadPoolException):
                e.print_excs()
                log.debug(e.format_excs())
            else:
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

    def _validate(self):
        """
        Checks that all cluster template settings are valid. Raises a
        ClusterValidationError exception if not.
        """
        log.info("Validating cluster template settings...")
        try:
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
            log.info('Cluster template settings are valid')
            return True
        except exception.ClusterValidationError, e:
            e.msg = 'Cluster settings are not valid:\n%s' % e.msg
            raise

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
                "total number of nodes specified in node_instance_type (%s) "
                "must be <= cluster_size-1 (%s)" % (num_itypes, num_nodes))
        return True

    def _validate_shell_setting(self):
        cluster_shell = self.cluster_shell
        if not self.__available_shells.get(cluster_shell):
            raise exception.ClusterValidationError(
                'Invalid user shell specified. Options are %s' %
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
                log.warn('The availability_zone = %s '
                         'is not available at this time' % zone)
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
        image_is_hvm = (image.virtualization_type == "hvm")
        if image_is_hvm and not instance_type in static.CLUSTER_TYPES:
            cctypes_list = ', '.join(static.CLUSTER_TYPES)
            raise exception.ClusterValidationError(
                "Image '%s' is a Cluster Compute/GPU image (HVM) and cannot "
                "be used with instance type '%s'\nThe instance type "
                "for a Cluster Compute/GPU image (HVM) must be one of: %s" %
                (image_id, instance_type, cctypes_list))
        instance_platforms = self.__instance_types[instance_type]
        if image_platform not in instance_platforms:
            error_msg = "Instance type %(instance_type)s is for an " \
                        "%(instance_platform)s platform while " \
                        "%(image_id)s is an %(image_platform)s platform"
            error_dict = {'instance_type': instance_type,
                          'instance_platform': ', '.join(instance_platforms),
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
                "You specified an invalid node_instance_type %s\n"
                "Possible options are:\n%s" %
                (node_instance_type, instance_type_list))
        elif master_instance_type:
            if not master_instance_type in instance_types:
                raise exception.ClusterValidationError(
                    "You specified an invalid master_instance_type %s\n"
                    "Possible options are:\n%s" %
                    (master_instance_type, instance_type_list))
        try:
            self.__check_platform(node_image_id, node_instance_type)
        except exception.ClusterValidationError, e:
            raise exception.ClusterValidationError(
                'Incompatible node_image_id and node_instance_type:\n' + e.msg)
        if master_image_id and not master_instance_type:
            try:
                self.__check_platform(master_image_id, node_instance_type)
            except exception.ClusterValidationError, e:
                raise exception.ClusterValidationError(
                    'Incompatible master_image_id and node_instance_type\n' +
                    e.msg)
        elif master_image_id and master_instance_type:
            try:
                self.__check_platform(master_image_id, master_instance_type)
            except exception.ClusterValidationError, e:
                raise exception.ClusterValidationError(
                    'Incompatible master_image_id and master_instance_type\n' +
                    e.msg)
        elif master_instance_type and not master_image_id:
            try:
                self.__check_platform(node_image_id, master_instance_type)
            except exception.ClusterValidationError, e:
                raise exception.ClusterValidationError(
                    'Incompatible node_image_id and master_instance_type\n' +
                    e.msg)
        for itype in self.node_instance_types:
            type = itype.get('type')
            img = itype.get('image') or node_image_id
            if not type in instance_types:
                raise exception.ClusterValidationError(
                    "You specified an invalid instance type %s\n"
                    "Possible options are:\n%s" % (type, instance_type_list))
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
            if type in static.CLUSTER_TYPES:
                img = self.ec2.get_image(image)
                if img.virtualization_type != 'hvm':
                    raise exception.ClusterValidationError(
                        'Cluster Compute/GPU instance type %s '
                        'can only be used with HVM images.\n'
                        'Image %s is NOT an HVM image.' % (type, image))

    def _validate_ebs_aws_settings(self):
        """
        Verify EBS volumes exists and that each volume's zone matches this
        cluster's zone setting.
        """
        for vol in self.volumes:
            v = self.volumes.get(vol)
            vol_id = v.get('volume_id')
            vol = self.ec2.get_volume(vol_id)
            if vol.status != 'available':
                try:
                    if vol.attach_data.instance_id == self.master_node.id:
                        continue
                except exception.MasterDoesNotExist:
                    pass
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
            if not iptools.validate_cidr(cidr_ip):
                raise exception.InvalidCIDRSpecified(cidr_ip)

    def _validate_ebs_settings(self):
        """
        Check EBS vols for missing/duplicate DEVICE/PARTITION/MOUNT_PATHs
        and validate these settings. Does not require AWS credentials.
        """
        volmap = {}
        devmap = {}
        mount_paths = []
        for vol in self.volumes:
            vol_name = vol
            vol = self.volumes.get(vol)
            vol_id = vol.get('volume_id')
            device = vol.get('device')
            partition = vol.get('partition')
            mount_path = vol.get("mount_path")
            vmap = volmap.get(vol_id, {})
            devices = vmap.get('device', [])
            partitions = vmap.get('partition', [])
            if devices and device not in devices:
                raise exception.ClusterValidationError(
                    "Can't attach volume %s to more than one device" % vol_id)
            elif partitions and partition in partitions:
                raise exception.ClusterValidationError(
                    "Multiple configurations for %s\n"
                    "Either pick one or specify a separate partition for "
                    "each configuration" % vol_id)
            vmap['partition'] = partitions + [partition]
            vmap['device'] = devices + [device]
            volmap[vol_id] = vmap
            dmap = devmap.get(device, {})
            vol_ids = dmap.get('volume_id', [])
            if vol_ids and vol_id not in vol_ids:
                raise exception.ClusterValidationError(
                    "Can't attach more than one volume on device %s" % device)
            dmap['volume_id'] = vol_ids + [vol_id]
            devmap[device] = dmap
            mount_paths.append(mount_path)
            if not device:
                raise exception.ClusterValidationError(
                    'Missing DEVICE setting for volume %s' % vol_name)
            if not utils.is_valid_device(device):
                raise exception.ClusterValidationError(
                    "Invalid DEVICE value for volume %s" % vol_name)
            if partition:
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
        for path in mount_paths:
            if mount_paths.count(path) > 1:
                raise exception.ClusterValidationError(
                    "Can't mount more than one volume on %s" % path)
        return True

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
                "key_location '%s' does not exist" % key_location)
        elif not os.path.isfile(key_location):
            raise exception.ClusterValidationError(
                "key_location '%s' is not a file" % key_location)
        keyname = self.keyname
        keypair = self.ec2.get_keypair_or_none(keyname)
        if not keypair:
            raise exception.ClusterValidationError(
                "Account does not contain a key with keyname: %s" % keyname)
        fingerprint = keypair.fingerprint
        if len(fingerprint) == 59:
            localfingerprint = ssh.get_private_rsa_fingerprint(key_location)
            if localfingerprint != fingerprint:
                raise exception.ClusterValidationError(
                    "Incorrect fingerprint for key_location '%s'\n\n"
                    "local fingerprint: %s\n\nkeypair fingerprint: %s"
                    % (key_location, localfingerprint, fingerprint))
        else:
            # Skip fingerprint validation for keys created using EC2 import
            # keys until I can figure out the mystery behind the import keys
            # fingerprint. I'm able to match ssh-keygen's public key
            # fingerprint, however, Amazon doesn't for some reason...
            log.warn("Skipping keypair fingerprint validation...")
        if self.zone:
            z = self.ec2.get_zone(self.zone)
            if keypair.region != z.region:
                raise exception.ClusterValidationError(
                    'Keypair %s not in availability zone region %s' %
                    (keyname, z.region))
        return True

    def ssh_to_master(self, user='root', command=None):
        return self.ssh_to_node('master', user=user, command=command)

    def ssh_to_node(self, alias, user='root', command=None):
        node = self.get_node_by_alias(alias)
        node = node or self.get_node_by_dns_name(alias)
        node = node or self.get_node_by_id(alias)
        if not node:
            raise exception.InstanceDoesNotExist(alias, label='node')
        if command:
            orig_user = node.ssh.get_current_user()
            node.ssh.switch_user(user)
            node.ssh.execute(command, silent=False)
            node.ssh.switch_user(orig_user)
            return node.ssh.get_last_status()
        else:
            node.shell(user=user)

if __name__ == "__main__":
    from starcluster.config import StarClusterConfig
    cfg = StarClusterConfig().load()
    sc = cfg.get_cluster_template('smallcluster', 'mynewcluster')
    if sc.is_valid():
        sc.start(create=True)
