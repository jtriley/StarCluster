# Copyright 2009-2014 Justin Riley
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

import os
import re
import time
import string
import pprint
import warnings
import datetime
import json
from collections import Counter

import iptools

from starcluster import utils
from starcluster import static
from starcluster import sshutils
from starcluster import managers
from starcluster import userdata
from starcluster import deathrow
from starcluster import exception
from starcluster import threadpool
from starcluster import validators
from starcluster import progressbar
from starcluster import clustersetup
from starcluster.node import Node
from starcluster.node import NodeManager
from starcluster.plugins import sge
from starcluster.utils import print_timing
from starcluster.templates import user_msgs
from starcluster.logger import log
from starcluster.streaming_node_add import streaming_add


class ClusterManager(managers.Manager):
    """
    Manager class for Cluster objects
    """
    def __repr__(self):
        return "<ClusterManager: %s>" % self.ec2.region.name

    def get_cluster(self, cluster_name, group=None, load_receipt=True,
                    load_plugins=True, load_volumes=True, require_keys=True):
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

            # Useful when config is on master node
            try:
                cl.key_location = \
                    self.cfg.get_key(cl.master_node.key_name)\
                        .get('key_location')
            except (exception.KeyNotFound, exception.MasterDoesNotExist):
                if require_keys:
                    raise
                cl.key_location = ''

            if load_receipt:
                cl.load_receipt(load_plugins=load_plugins,
                                load_volumes=load_volumes)
            try:
                cl.keyname = cl.keyname or cl.master_node.key_name
                key_location = self.cfg.get_key(cl.keyname).get('key_location')
                cl.key_location = key_location
                if require_keys:
                    cl.validator.validate_keypair()
            except (exception.KeyNotFound, exception.MasterDoesNotExist):
                if require_keys:
                    raise
                cl.key_location = ''
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

    def ssh_to_master(self, cluster_name, user='root', command=None,
                      forward_x11=False, forward_agent=False,
                      pseudo_tty=False):
        """
        ssh to master node of cluster_name

        user keyword specifies an alternate user to login as
        """
        cluster = self.get_cluster(cluster_name, load_receipt=False,
                                   require_keys=True)
        return cluster.ssh_to_master(user=user, command=command,
                                     forward_x11=forward_x11,
                                     forward_agent=forward_agent,
                                     pseudo_tty=pseudo_tty)

    def ssh_to_cluster_node(self, cluster_name, node_id, user='root',
                            command=None, forward_x11=False,
                            forward_agent=False, pseudo_tty=False):
        """
        ssh to a node in cluster_name that has either an id,
        dns name, or alias matching node_id

        user keyword specifies an alternate user to login as
        """
        cluster = self.get_cluster(cluster_name, load_receipt=False,
                                   require_keys=False)
        node = cluster.get_node(node_id)
        key_location = self.cfg.get_key(node.key_name).get('key_location')
        cluster.key_location = key_location
        cluster.keyname = node.key_name
        cluster.validator.validate_keypair()
        return node.shell(user=user, forward_x11=forward_x11,
                          forward_agent=forward_agent,
                          pseudo_tty=pseudo_tty, command=command)

    def _get_cluster_name(self, cluster_name):
        """
        Returns human readable cluster name/tag prefixed with '@sc-'
        """
        if not cluster_name.startswith(static.SECURITY_GROUP_PREFIX):
            cluster_name = static.SECURITY_GROUP_TEMPLATE % cluster_name
        return cluster_name

    def add_node(self, cluster_name, alias=None, no_create=False,
                 image_id=None, instance_type=None, zone=None,
                 placement_group=None, spot_bid=None, reboot_interval=10,
                 n_reboot_restart=False):
        cl = self.get_cluster(cluster_name)
        return cl.add_node(alias=alias, image_id=image_id,
                           instance_type=instance_type, zone=zone,
                           placement_group=placement_group, spot_bid=spot_bid,
                           no_create=no_create,
                           reboot_interval=reboot_interval,
                           n_reboot_restart=n_reboot_restart)

    def add_nodes(self, cluster_name, num_nodes, aliases=None, no_create=False,
                  image_id=None, instance_type=None, zone=None,
                  placement_group=None, spot_bid=None, reboot_interval=10,
                  n_reboot_restart=False):
        """
        Add one or more nodes to cluster
        """
        cl = self.get_cluster(cluster_name)
        return cl.add_nodes(num_nodes, aliases=aliases, image_id=image_id,
                            instance_type=instance_type, zone=zone,
                            placement_group=placement_group, spot_bid=spot_bid,
                            no_create=no_create,
                            reboot_interval=reboot_interval,
                            n_reboot_restart=n_reboot_restart)

    def remove_node(self, cluster_name, alias=None, terminate=True,
                    force=False):
        """
        Remove a single node from a cluster
        """
        cl = self.get_cluster(cluster_name)
        n = cl.get_node(alias) if alias else None
        return cl.remove_node(node=n, terminate=terminate, force=force)

    def remove_nodes(self, cluster_name, num_nodes=None, aliases=None,
                     terminate=True, force=False):
        """
        Remove one or more nodes from cluster
        """
        cl = self.get_cluster(cluster_name)
        nodes = cl.get_nodes(aliases) if aliases else None
        return cl.remove_nodes(nodes=nodes, num_nodes=num_nodes,
                               terminate=terminate, force=force)

    def restart_cluster(self, cluster_name, reboot_only=False):
        """
        Reboots and reconfigures cluster_name
        """
        cl = self.get_cluster(cluster_name)
        cl.restart_cluster(reboot_only=reboot_only)

    def stop_cluster(self, cluster_name, terminate_unstoppable=False,
                     force=False):
        """
        Stop an EBS-backed cluster
        """
        cl = self.get_cluster(cluster_name, load_receipt=not force,
                              require_keys=not force)
        cl.stop_cluster(terminate_unstoppable, force=force)

    def terminate_cluster(self, cluster_name, force=False):
        """
        Terminates cluster_name
        """
        cl = self.get_cluster(cluster_name, load_receipt=not force,
                              require_keys=not force)
        cl.terminate_cluster(force=force)

    def get_cluster_security_group(self, group_name):
        """
        Return cluster security group by appending '@sc-' to group_name and
        querying EC2.
        """
        gname = self._get_cluster_name(group_name)
        return self.ec2.get_security_group(gname)

    def get_cluster_group_or_none(self, group_name):
        try:
            return self.get_cluster_security_group(group_name)
        except exception.SecurityGroupDoesNotExist:
            pass

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
        regex = re.compile('^' + static.SECURITY_GROUP_TEMPLATE % '(.*)')
        match = regex.match(sg)
        tag = None
        if match:
            tag = match.groups()[0]
        if not tag:
            raise ValueError("Invalid cluster group name: %s" % sg)
        return tag

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
                                      load_volumes=False, require_keys=False)
            except exception.IncompatibleCluster as e:
                sep = '*' * 60
                log.error('\n'.join([sep, e.msg, sep]),
                          extra=dict(__textwrap__=True))
                print
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
            if scg.vpc_id:
                print 'VPC: %s' % scg.vpc_id
                print 'Subnet: %s' % getattr(n, 'subnet_id', 'N/A')
            print 'Zone: %s' % getattr(n, 'placement', 'N/A')
            print 'Keypair: %s' % getattr(n, 'key_name', 'N/A')
            ebs_vols = []
            for node in nodes:
                devices = node.attached_vols
                if not devices:
                    continue
                node_id = node.alias or node.id
                for dev in devices:
                    d = devices.get(dev)
                    vol_id = d.volume_id
                    status = d.status
                    ebs_vols.append((vol_id, node_id, dev, status))
            if ebs_vols:
                print 'EBS volumes:'
                for vid, nid, dev, status in ebs_vols:
                    print('    %s on %s:%s (status: %s)' %
                          (vid, nid, dev, status))
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
                                                     node.id, node.addr or '')
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

    def run_plugin(self, plugin_name, cluster_tag, args=[]):
        """
        Run a plugin defined in the config.

        plugin_name must match the plugin's section name in the config
        cluster_tag specifies the cluster to run the plugin on
        """
        cl = self.get_cluster(cluster_tag, load_plugins=False)
        if not cl.is_cluster_up():
            raise exception.ClusterNotRunning(cluster_tag)
        plugs = [self.cfg.get_plugin(plugin_name)]
        plug = deathrow._load_plugins(plugs)[0]
        cl.run_plugin(plug, name=plugin_name, args=args)


class Cluster(object):

    def __init__(self,
                 ec2_conn=None,
                 spot_bid=None,
                 cluster_tag=None,
                 cluster_description=None,
                 cluster_size=None,
                 cluster_user=None,
                 cluster_shell=None,
                 dns_prefix=None,
                 master_image_id=None,
                 master_instance_type=None,
                 node_image_id=None,
                 node_instance_type=None,
                 availability_zone=None,
                 keyname=None,
                 key_location=None,
                 volumes=[],
                 plugins=None,
                 permissions=[],
                 userdata_scripts=[],
                 refresh_interval=30,
                 disable_queue=False,
                 num_threads=20,
                 disable_threads=False,
                 cluster_group=None,
                 force_spot_master=False,
                 disable_cloudinit=False,
                 subnet_ids=[],
                 public_ips=None,
                 plugins_order=[],
                 config_on_master=False,
                 dns_suffix=None,
                 node_instance_array=[],
                 impaired_threshold_sec=120):
        # update class vars with given vars
        _vars = locals().copy()
        for k in ['cluster_group', 'ec2_conn', 'node_image_id',
                  'node_instance_type', 'spot_bid']:
            del _vars[k]
        self.__dict__.update(_vars)

        # more configuration
        now = time.strftime("%Y%m%d%H%M")
        if self.cluster_tag is None:
            self.cluster_tag = "cluster%s" % now
        if cluster_description is None:
            self.cluster_description = "Cluster created at %s" % now
        self.ec2 = ec2_conn
        self.cluster_size = cluster_size or 0
        self.volumes = self.load_volumes(volumes)
        self.plugins = self.load_plugins(plugins)
        self.userdata_scripts = userdata_scripts or []
        self.dns_prefix = dns_prefix and cluster_tag
        self.refresh_interval = refresh_interval
        self.disable_queue = disable_queue
        self.num_threads = num_threads
        self.disable_threads = disable_threads
        self.force_spot_master = force_spot_master
        self.disable_cloudinit = disable_cloudinit
        self.plugins_order = plugins_order
        self.dns_suffix = dns_suffix and cluster_tag
        if node_instance_array:
            try:
                assert node_image_id is None
                assert node_instance_type is None
            except Exception as e:
                log.error("Cannot have both node_instance_array and node "
                          "details defined", exc_info=True)
                raise e
        else:
            self.set_default_node_instance_array(node_image_id,
                                                 node_instance_type, spot_bid)
        self._cluster_group = None
        self._placement_group = None
        self._zone = None
        self._master = None
        self._nodes = []
        self._pool = None
        self._progress_bar = None
        self.__default_plugin = None
        self.__sge_plugin = None
        self._vpc_id = None
        self._subnet_zones_mapping = None
        self._impaired_nodes = {}
        self._impaired_threshold_sec = impaired_threshold_sec

    def __repr__(self):
        return '<Cluster: %s (%s-node)>' % (self.cluster_tag,
                                            self.cluster_size)

    def set_default_node_instance_array(self, image_id, instance_type,
                                        spot_bid):
        self.node_instance_array = [{
            'image_id': image_id,
            'instance_type': instance_type,
            'spot_bid': spot_bid,
            'selection_factor': 1,
            'size': 0
        }]

    @property
    def node_image_id(self):
        return self.node_instance_array[0]['image_id']

    @property
    def node_instance_type(self):
        return self.node_instance_array[0]['instance_type']

    @property
    def spot_bid(self):
        return self.node_instance_array[0].get('spot_bid', None)

    @property
    def zone(self):
        if not self._zone:
            self._zone = self._get_cluster_zone()
        return self._zone

    def _get_cluster_zone(self):
        """
        Returns the cluster's zone. If volumes are specified, this method
        determines the common zone between those volumes. If a zone is
        explicitly specified in the config and does not match the common zone
        of the volumes, an exception is raised. If all volumes are not in the
        same zone an exception is raised. If no volumes are specified, returns
        the user-specified zone if it exists. Returns None if no volumes and no
        zone is specified.
        """
        zone = None
        if self.availability_zone:
            zone = self.ec2.get_zone(self.availability_zone)
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
        if common_zone and zone and zone.name != common_zone:
            raise exception.InvalidZone(zone.name, common_zone)
        if not zone and common_zone:
            zone = self.ec2.get_zone(common_zone)
        if not zone:
            try:
                zone = self.ec2.get_zone(self.master_node.placement)
            except exception.MasterDoesNotExist:
                pass
        return zone

    @property
    def _plugins(self):
        return [p.__plugin_metadata__ for p in self.plugins]

    def load_plugins(self, plugins):
        if plugins and isinstance(plugins[0], dict):
            warnings.warn("In a future release the plugins kwarg for Cluster "
                          "will require a list of plugin objects and not a "
                          "list of dicts", DeprecationWarning)
            plugins = deathrow._load_plugins(plugins)
        return plugins

    @property
    def _default_plugin(self):
        if not self.__default_plugin:
            self.__default_plugin = clustersetup.DefaultClusterSetup(
                disable_threads=self.disable_threads,
                num_threads=self.num_threads)
        return self.__default_plugin

    @property
    def _sge_plugin(self):
        if not self.__sge_plugin:
            self.__sge_plugin = sge.SGEPlugin(
                disable_threads=self.disable_threads,
                num_threads=self.num_threads)
        return self.__sge_plugin

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
                # rm user-defined devices from the list of auto-assigned
                # devices
                devices.remove(dev)
            volid = vol.get('volume_id')
            if dev and volid not in devmap:
                devmap[volid] = dev
        volumes = utils.AttributeDict()
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

    def update(self, kwargs, ignore_unknown=False):
        if 'node_instance_array' not in kwargs and 'node_image_id' in kwargs:
            self.set_default_node_instance_array(kwargs['node_image_id'],
                                                 kwargs['node_instance_type'],
                                                 kwargs['spot_bid'])
            for k in ['node_image_id', 'node_instance_type', 'spot_bid']:
                del kwargs[k]
        for key in kwargs.keys():
            if hasattr(self, key):
                self.__dict__[key] = kwargs[key]
            elif not ignore_unknown:
                msg = "Unknown configuration key: " + key
                log.error(msg)
                raise Exception("Unknown configuration key: " + key)

    def get(self, name):
        return self.__dict__.get(name)

    def __str__(self):
        cfg = self.__getstate__()
        return pprint.pformat(cfg)

    def print_config(self):
        core_settings, user_settings = self._get_settings()
        print "Core settings"
        print json.dumps(core_settings, indent=1, sort_keys=True)
        print
        print "User settings"
        print json.dumps(user_settings, indent=1, sort_keys=True)

    def load_receipt(self, load_plugins=True, load_volumes=True):
        """
        Load the original settings used to launch this cluster into this
        Cluster object. Settings are loaded from cluster group tags and the
        master node's user data.
        """
        try:
            tags = self.cluster_group.tags
            version = tags.get(static.VERSION_TAG, '')
            if utils.program_version_greater(version, static.VERSION):
                d = dict(cluster=self.cluster_tag, old_version=static.VERSION,
                         new_version=version)
                msg = user_msgs.version_mismatch % d
                sep = '*' * 60
                log.warn('\n'.join([sep, msg, sep]), extra={'__textwrap__': 1})
            self.update(self._get_settings_from_tags())
            if self.config_on_master:
                self._load_config_from_master()
            if not (load_plugins or load_volumes):
                return True
            try:
                master = self.master_node
            except exception.MasterDoesNotExist:
                unfulfilled_spots = [sr for sr in self.spot_requests if not
                                     sr.instance_id]
                if unfulfilled_spots:
                    self.wait_for_active_spots()
                    master = self.master_node
                else:
                    raise
            if load_plugins and self.plugins is None:
                self.plugins = self.load_plugins(
                    master.get_plugins(self.plugins_order))
            if load_volumes:
                self.volumes = master.get_volumes()
        except exception.PluginError:
            log.error("An error occurred while loading plugins: ",
                      exc_info=True)
            raise
        except exception.MasterDoesNotExist:
            raise
        except Exception:
            log.debug('load receipt exception: ', exc_info=True)
            raise exception.IncompatibleCluster(self.cluster_group)
        return True

    def __getstate__(self):
        cfg = {}
        exclude = ['key_location', 'plugins']
        include = ['_zone', '_plugins']
        for key in self.__dict__.keys():
            private = key.startswith('_')
            if (not private or key in include) and key not in exclude:
                val = getattr(self, key)
                if type(val) in [str, unicode, bool, int, float, list, dict]:
                    cfg[key] = val
                elif isinstance(val, utils.AttributeDict):
                    cfg[key] = dict(val)
        return cfg

    @property
    def _security_group(self):
        return static.SECURITY_GROUP_TEMPLATE % self.cluster_tag

    def get_vpc_id(self, subnet_id):
        subnet = self.ec2.get_subnet(self.subnet_ids[0])
        return subnet.vpc_id

    @property
    def vpc_id(self):
        if not self._vpc_id and self.subnet_ids:
            self._vpc_id = self.get_vpc_id(self.subnet_ids[0])
        return self._vpc_id

    @property
    def cluster_group(self):
        if self._cluster_group:
            return self._cluster_group
        sg = self.ec2.get_group_or_none(self._security_group)
        if not sg:
            desc = 'StarCluster-%s' % static.VERSION.replace('.', '_')
            if self.subnet_ids:
                desc += ' (VPC)'
            sg = self.ec2.create_group(self._security_group,
                                       description=desc,
                                       auth_ssh=True,
                                       auth_group_traffic=True,
                                       vpc_id=self.vpc_id)
            self._add_tags_to_sg(sg)
        self._add_permissions_to_sg(sg)
        self._cluster_group = sg
        return sg

    @property
    def subnets_mapping(self):
        if self._subnet_zones_mapping is None:
            mapping = {}
            for subnet_id in self.subnet_ids:
                mapping[subnet_id] = self.ec2.get_subnet(subnet_id)
            self._subnet_zones_mapping = mapping
        return self._subnet_zones_mapping

    def _add_permissions_to_sg(self, sg):
        ssh_port = static.DEFAULT_SSH_PORT
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
            else:
                log.info("Already open: %s port range %s-%s for CIDR %s" %
                         (ip_protocol, from_port, to_port, cidr_ip))
            includes_ssh = from_port <= ssh_port <= to_port
            open_to_world = cidr_ip == static.WORLD_CIDRIP
            if ip_protocol == 'tcp' and includes_ssh and not open_to_world:
                sg.revoke(ip_protocol, ssh_port, ssh_port,
                          static.WORLD_CIDRIP)

    def _add_chunked_tags(self, sg, chunks, base_tag_name):
        for i, chunk in enumerate(chunks):
            tag = "%s-%s" % (base_tag_name, i) if i != 0 else base_tag_name
            if tag not in sg.tags:
                sg.add_tag(tag, chunk)

    def _get_settings(self):
        """
        The settings to save
        """
        core_settings = dict(cluster_size=self.cluster_size,
                             master_image_id=self.master_image_id,
                             master_instance_type=self.master_instance_type,
                             node_instance_array=self.node_instance_array,
                             availability_zone=self.availability_zone,
                             dns_prefix=self.dns_prefix,
                             subnet_ids=self.subnet_ids,
                             public_ips=self.public_ips,
                             disable_queue=self.disable_queue,
                             disable_cloudinit=self.disable_cloudinit,
                             plugins_order=self.plugins_order,
                             dns_suffix=self.dns_suffix)
        user_settings = dict(cluster_user=self.cluster_user,
                             cluster_shell=self.cluster_shell,
                             keyname=self.keyname)
        return core_settings, user_settings

    def _add_tags_to_sg(self, sg):
        if static.VERSION_TAG not in sg.tags:
            sg.add_tag(static.VERSION_TAG, str(static.VERSION))
        if self.config_on_master:
            # the only info we store is the fact that config is on master
            core = utils.dump_compress_encode(
                dict(config_on_master=self.config_on_master),
                use_json=True, chunk_size=static.MAX_TAG_LEN)
            self._add_chunked_tags(sg, core, static.CORE_TAG)
        else:
            core_settings, user_settings = self._get_settings()
            core = utils.dump_compress_encode(core_settings, use_json=True,
                                              chunk_size=static.MAX_TAG_LEN)
            self._add_chunked_tags(sg, core, static.CORE_TAG)
            user = utils.dump_compress_encode(user_settings, use_json=True,
                                              chunk_size=static.MAX_TAG_LEN)
            self._add_chunked_tags(sg, user, static.USER_TAG)

    def _load_chunked_tags(self, sg, base_tag_name):
        tags = [i for i in sg.tags if i.startswith(base_tag_name)]
        tags.sort()
        chunks = [sg.tags[i] for i in tags if i.startswith(base_tag_name)]
        return utils.decode_uncompress_load(chunks, use_json=True)

    def _get_settings_from_tags(self, sg=None):
        sg = sg or self.cluster_group
        cluster = {}
        if static.CORE_TAG in sg.tags:
            cluster.update(self._load_chunked_tags(sg, static.CORE_TAG))
        if static.USER_TAG in sg.tags:
            cluster.update(self._load_chunked_tags(sg, static.USER_TAG))
        return cluster

    def save_config_on_master(self):
        """
        Vanilla Improvements function - save the config on the master node.
        For cluster saving their config on the master node rather than in
        the security group tags. No more chunk/hashing/splitting headaches.
        """
        log.info("Saving config on master")
        settings, user_settings = self._get_settings()
        settings.update(user_settings)
        settings["plugins"] = self._plugins
        config = self.master_node.ssh.remote_file(static.MASTER_CFG_FILE, 'wt')
        json.dump(settings, config, indent=4, separators=(',', ': '),
                  sort_keys=True)
        config.close()

    def _load_config_from_master(self):
        """
        Vanilla Improvements function - loads the config on the master node.
        """
        config = self.master_node.ssh.remote_file(static.MASTER_CFG_FILE, 'rt')
        loaded_config = json.load(config)
        self.plugins_order = loaded_config["plugins"]
        self.update(loaded_config)
        config.close()
        master = self.master_node
        self.plugins = self.load_plugins(
            master.get_plugins(self.plugins_order, loaded_config["plugins"]))
        self.validate()

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
        self._master.key_location = self.key_location
        return self._master

    def _get_duplicate_aliases(self):
        aliases = [_n.alias for _n in self.nodes]
        tmp_aliases = Counter(aliases)
        return filter(lambda k: tmp_aliases[k] > 1, tmp_aliases)

    @property
    def nodes(self):
        states = ['pending', 'running']
        filters = {'instance-state-name': states,
                   'instance.group-name': self._security_group}
        nodes = self.ec2.get_all_instances(filters=filters)

        def filter_fct(n):
            if self._security_group in [g.name for g in n.groups]:
                return True
            log.warning("EC2 issue? Got instance not in security group. "
                        "Filtering out.")
            return False
        nodes = filter(filter_fct, nodes)

        # remove any cached nodes not in the current node list from EC2
        current_ids = [n.id for n in nodes]

        # If a node was terminated due to error, even if it still shows up,
        # ignore it
        to_remove = set()
        for id in NodeManager.nodes_id_ignore:
            if id in current_ids:
                log.info("Ignoring node id [" + id + "]")
                del current_ids[current_ids.index(id)]
            else:
                log.info("Node id [" + id + "] is gone.")
                to_remove.add(id)

        for id in to_remove:
            NodeManager.nodes_id_ignore.remove(id)
        del to_remove

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

    def get_nodes_or_raise(self, nodes=None):
        _nodes = self.nodes
        if not _nodes:
            filters = {'instance.group-name': self._security_group}
            terminated_nodes = self.ec2.get_all_instances(filters=filters)
            raise exception.NoClusterNodesFound(terminated_nodes)
        if nodes:
            nodes_ids = [n.id for n in nodes]
            _nodes = filter(lambda n: n.id in nodes_ids, _nodes)
        return _nodes

    def get_node(self, identifier, nodes=None):
        """
        Returns a node if the identifier specified matches any unique instance
        attribute (e.g. instance id, alias, spot id, dns name, private ip,
        public ip, etc.)
        """
        nodes = nodes or self.nodes
        for node in self.nodes:
            if node.alias == identifier:
                return node
            if node.id == identifier:
                return node
            if node.spot_id == identifier:
                return node
            if node.dns_name == identifier:
                return node
            if node.ip_address == identifier:
                return node
            if node.private_ip_address == identifier:
                return node
            if node.public_dns_name == identifier:
                return node
            if node.private_dns_name == identifier:
                return node
        raise exception.InstanceDoesNotExist(identifier, label='node')

    def get_nodes(self, identifiers, nodes=None):
        """
        Same as get_node but takes a list of identifiers and returns a list of
        nodes.
        """
        nodes = nodes or self.nodes
        node_list = []
        for i in identifiers:
            n = self.get_node(i, nodes=nodes)
            if n in node_list:
                continue
            else:
                node_list.append(n)
        return node_list

    def get_node_by_dns_name(self, dns_name, nodes=None):
        warnings.warn("Please update your code to use Cluster.get_node()",
                      DeprecationWarning)
        return self.get_node(dns_name, nodes=nodes)

    def get_node_by_id(self, instance_id, nodes=None):
        warnings.warn("Please update your code to use Cluster.get_node()",
                      DeprecationWarning)
        return self.get_node(instance_id, nodes=nodes)

    def get_node_by_alias(self, alias, nodes=None):
        warnings.warn("Please update your code to use Cluster.get_node()",
                      DeprecationWarning)
        return self.get_node(alias, nodes=nodes)

    def _nodes_in_states(self, states):
        return filter(lambda x: x.state in states, self.nodes)

    def _make_alias(self, id=None, master=False):
        if master:
            alias = "master"
        elif id is not None:
            alias = 'node{:03d}'.format(id)
        else:
            raise AttributeError("_make_alias(...) must receive either"
                                 " master=True or a node id number")

        if self.dns_prefix:
            alias = "{}-{}".format(self.dns_prefix, alias)
        if self.dns_suffix:
            alias = "{}.{}".format(alias, self.dns_suffix)
        return alias

    @property
    def running_nodes(self):
        return self._nodes_in_states(['running'])

    @property
    def stopped_nodes(self):
        return self._nodes_in_states(['stopping', 'stopped'])

    @property
    def spot_requests(self):
        group_id = self.cluster_group.id
        states = ['active', 'open']
        filters = {'state': states}
        vpc_id = self.cluster_group.vpc_id
        if vpc_id and self.subnet_ids:
            # According to the EC2 API docs this *should* be
            # launch.network-interface.group-id but it doesn't work
            filters['network-interface.group-id'] = group_id
        else:
            filters['launch.group-id'] = group_id
        return self.ec2.get_all_spot_requests(filters=filters)

    def get_spot_requests_or_raise(self, spots):
        _spots = self.spot_requests
        if not _spots:
            raise exception.NoClusterSpotRequests
        if spots:
            spots_ids = [s.id for s in spots]
            _spots = filter(lambda s: s.id in spots_ids, _spots)
        return _spots

    def create_node(self, alias, image_id=None, instance_type=None, zone=None,
                    placement_group=None, spot_bid=None, force_flat=False):
        return self.create_nodes([alias], image_id=image_id,
                                 instance_type=instance_type, zone=zone,
                                 placement_group=placement_group,
                                 spot_bid=spot_bid, force_flat=force_flat)[0]

    def _get_cluster_userdata(self, aliases):
        alias_file = utils.string_to_file('\n'.join(['#ignored'] + aliases),
                                          static.UD_ALIASES_FNAME)
        plugins = utils.dump_compress_encode(self._plugins)
        plugins_file = utils.string_to_file('\n'.join(['#ignored', plugins]),
                                            static.UD_PLUGINS_FNAME)
        volumes = utils.dump_compress_encode(self.volumes)
        volumes_file = utils.string_to_file('\n'.join(['#ignored', volumes]),
                                            static.UD_VOLUMES_FNAME)
        udfiles = [alias_file, plugins_file, volumes_file]
        user_scripts = self.userdata_scripts or []
        udfiles += [open(f) for f in user_scripts]
        use_cloudinit = not self.disable_cloudinit
        udata = userdata.bundle_userdata_files(udfiles,
                                               use_cloudinit=use_cloudinit)
        log.debug('Userdata size in KB: %.2f' % utils.size_in_kb(udata))
        return udata

    def select_instance_and_zone(self):
        selection = None
        zones_filter = None
        if self.subnet_ids:
            zones_filter = [s_net.availability_zone
                            for s_net in self.subnets_mapping.values()]

        for i in self.node_instance_array:
            zone, price = self.ec2.get_spot_cheapest_zone(
                i['instance_type'], zones_filter, vpc=self.vpc_id is not None)
            log.debug("%s %s: %f", i['instance_type'], zone, price)
            if selection is None or (
                    price < i['spot_bid'] and
                    selection['price'] * selection['selection_factor']
                    > price * i.get('selection_factor', 1)):
                selection = {
                    'zone': zone,
                    'price': price,
                    'instance_type': i['instance_type'],
                    'image_id': i['image_id'],
                    'spot_bid': i['spot_bid'],
                    'selection_factor': i.get('selection_factor', 1)
                }
        assert selection is not None
        return selection

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
        auto_select_instance_type = instance_type is None
        instance_type = instance_type or self.node_instance_type
        if placement_group or instance_type in static.PLACEMENT_GROUP_TYPES:
            region = self.ec2.region.name
            if region not in static.PLACEMENT_GROUP_REGIONS:
                cluster_regions = ', '.join(static.PLACEMENT_GROUP_REGIONS)
                log.warn("Placement groups are only supported in the "
                         "following regions:\n%s" % cluster_regions)
                log.warn("Instances will not be launched in a placement group")
                placement_group = None
            elif placement_group is None:
                # if placement_group is False -> leave false
                placement_group = self.placement_group.name
        availability_zone_group = None if placement_group is False \
            else cluster_sg
        # launch_group is related to placement group
        launch_group = availability_zone_group

        if spot_bid and not placement_group and zone is None:
            if auto_select_instance_type:
                selection = self.select_instance_and_zone()
                zone = selection['zone']
                price = selection['price']
                instance_type = selection['instance_type']
                log.info("Selected instance type %s with minimal price of %f "
                         "in zone %s", instance_type, selection['price'],
                         zone)
            else:
                zones_filter = None
                if self.subnet_ids:
                    zones_filter = [s_net.availability_zone
                                    for s_net in self.subnets_mapping.values()]
                zone, price = self.ec2.get_spot_cheapest_zone(
                    instance_type, zones_filter,
                    vpc=self.vpc_id is not None)
                log.info("Min price of %f found in zone %s", price, zone)
            if price > spot_bid:
                # Let amazon pick the first zone where the prices goes
                # bellow the spot_bid
                log.info("Reverting to \"no zone\" as the min price is "
                         "above the spot bid.")
                zone = None
        elif zone is None:
            # Make sure master is in the same zone as the volumes mounted by
            # the cluster.
            zone = getattr(self.zone, 'name', None)

        image_id = image_id or self.node_image_id
        count = len(aliases) if not spot_bid else 1
        user_data = self._get_cluster_userdata(aliases)
        kwargs = dict(price=spot_bid, instance_type=instance_type,
                      min_count=count, max_count=count, count=count,
                      key_name=self.keyname,
                      availability_zone_group=availability_zone_group,
                      launch_group=launch_group,
                      placement=zone,
                      user_data=user_data,
                      placement_group=placement_group)
        if self.subnet_ids:
            subnet_id = self.subnet_ids[0]  # default subnet
            if zone:
                found = False
                for s_id, s_net in self.subnets_mapping.iteritems():
                    if s_net.availability_zone == zone:
                        found = True
                        subnet_id = s_id
                        break
                assert found
            netif = self.ec2.get_network_spec(
                device_index=0, associate_public_ip_address=self.public_ips,
                subnet_id=subnet_id, groups=[self.cluster_group.id])
            kwargs.update(
                network_interfaces=self.ec2.get_network_collection(netif))
        else:
            kwargs.update(security_groups=[cluster_sg])
        resvs = []
        if spot_bid:
            security_group_id = self.cluster_group.id
            for alias in aliases:
                if not self.subnet_ids:
                    kwargs['security_group_ids'] = [security_group_id]
                kwargs['user_data'] = self._get_cluster_userdata([alias])
                resvs.extend(self.ec2.request_instances(image_id, **kwargs))
        else:
            resvs.append(self.ec2.request_instances(image_id, **kwargs))
        for resv in resvs:
            log.info(str(resv), extra=dict(__raw__=True))
        return resvs

    @classmethod
    def get_free_ids_among_nodes(cls, count, nodes):
        result = []
        if count == 0:
            return result
        ids = [int(re.search('node(\d{3})', n.alias).group(1)) for n in nodes]
        remaining = count
        for i in xrange(1, 1000):
            if i not in ids:
                result.append(i)
                remaining -= 1
            if remaining == 0:
                break
        assert len(result) == count
        return result

    def _get_free_node_nums(self, count):
        """
        Returns unused node ids
        """
        nodes = self._nodes_in_states(['pending', 'running'])
        nodes = filter(lambda x: not x.is_master(), nodes)
        return self.get_free_ids_among_nodes(count, nodes)

    def add_node(self, alias=None, no_create=False, image_id=None,
                 instance_type=None, zone=None, placement_group=None,
                 spot_bid=None, reboot_interval=10, n_reboot_restart=False):

        """
        Add a single node to this cluster
        """
        aliases = [alias] if alias else None
        return self.add_nodes(1, aliases=aliases, image_id=image_id,
                              instance_type=instance_type, zone=zone,
                              placement_group=placement_group,
                              spot_bid=spot_bid, no_create=no_create,
                              reboot_interval=reboot_interval,
                              n_reboot_restart=n_reboot_restart)

    def add_nodes(self, num_nodes, aliases=None, image_id=None,
                  instance_type=None, zone=None, placement_group=None,
                  spot_bid=None, no_create=False, reboot_interval=10,
                  n_reboot_restart=False):
        """
        Add new nodes to this cluster

        aliases - list of aliases to assign to new nodes (len must equal
        num_nodes)
        """
        running_pending = self._nodes_in_states(['pending', 'running'])
        aliases = aliases or []
        if not aliases:
            for i in self._get_free_node_nums(num_nodes):
                alias = self._make_alias(i)
                aliases.append(alias)
        assert len(aliases) == num_nodes
        if self._make_alias(master=True) in aliases:
            raise exception.ClusterValidationError(
                "worker nodes cannot have master as an alias")
        if no_create:
            self.wait_for_cluster(msg="Waiting for node(s) to come up...")
            log.debug("Adding node(s): %s" % aliases)
            for alias in aliases:
                node = self.get_node(alias)
                self.run_plugins(method_name="on_add_node", node=node)
        else:
            if self.subnet_ids:
                subnet = None
                tested = False
                for s_net in self.subnets_mapping.values():
                    if zone is None or s_net.availability_zone == zone:
                        tested = True
                        ip_count = s_net.available_ip_address_count
                        if ip_count < len(aliases):
                            raise exception.ClusterValidationError(
                                "Not enough IP addresses available in "
                                "%s (%d)" % (subnet.id, ip_count))
                assert tested
            for node in running_pending:
                if node.alias in aliases:
                    raise exception.ClusterValidationError(
                        "node with alias %s already exists" % node.alias)
            log.info("Launching node(s): %s" % ', '.join(aliases))
            resp = self.create_nodes(aliases, image_id=image_id,
                                     instance_type=instance_type, zone=zone,
                                     placement_group=placement_group,
                                     spot_bid=spot_bid)
            if spot_bid or self.spot_bid:
                streaming_add(self, spots=resp,
                              reboot_interval=reboot_interval,
                              n_reboot_restart=n_reboot_restart)
            else:
                streaming_add(self, instances=resp[0].instances,
                              reboot_interval=reboot_interval,
                              n_reboot_restart=n_reboot_restart)

        if all([not no_create, spot_bid, reboot_interval, n_reboot_restart]):
            # this will recreate the spot instances that might have died in
            # wait_for_cluster
            try_again_aliases = []
            while 1:
                for alias in aliases:
                    # verify all nodes were correctly added
                    try:
                        self.get_node_by_alias(alias)
                    except exception.InstanceDoesNotExist:
                        try_again_aliases.append(alias)
                if try_again_aliases:
                    log.info("Some spot instances have been terminated and "
                             "will be recreated.")
                    resp = self.create_nodes(try_again_aliases,
                                             image_id=image_id,
                                             instance_type=instance_type,
                                             zone=zone,
                                             placement_group=placement_group,
                                             spot_bid=spot_bid)
                    streaming_add(self, spots=resp,
                                  reboot_interval=reboot_interval,
                                  n_reboot_restart=n_reboot_restart)
                else:
                    # all nodes successfully created
                    break

    def remove_node(self, node=None, terminate=True, force=False):
        """
        Remove a single node from this cluster
        """
        nodes = [node] if node else None
        return self.remove_nodes(nodes=nodes, num_nodes=1, terminate=terminate,
                                 force=force)

    def remove_nodes(self, nodes=None, num_nodes=None, terminate=True,
                     force=False):
        """
        Remove a list of nodes from this cluster
        No step should prevent us to go further.
        """
        if nodes is None and num_nodes is None:
            raise exception.BaseException(
                "please specify either nodes or num_nodes kwargs")
        if not nodes:
            worker_nodes = self.nodes[1:]
            nodes = worker_nodes[-num_nodes:]
            nodes.reverse()
            if len(nodes) != num_nodes:
                raise exception.BaseException(
                    "cant remove %d nodes - only %d nodes exist" %
                    (num_nodes, len(worker_nodes)))
        else:
            for node in nodes:
                if node.is_master():
                    raise exception.InvalidOperation(
                        "cannot remove master node")
        for node in nodes:
            try:
                self.run_plugins(method_name="on_remove_node",
                                 node=node, reverse=True)
            except:
                # will still allow node termination
                pass
            if not terminate:
                continue
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
        lmap[(mtype, mimage)] = [self._make_alias(master=True)]
        id_start = 1
        for itype in self.node_instance_array:
            count = itype.get('size', 0)
            if not count:
                continue
            image_id = itype['image'] or self.node_image_id
            type = itype['type'] or self.node_instance_type
            if not (type, image_id) in lmap:
                lmap[(type, image_id)] = []
            for id in range(id_start, id_start + count):
                alias = self._make_alias(id)
                log.debug("Launch map: %s (ami: %s, type: %s)..." %
                          (alias, image_id, type))
                lmap[(type, image_id)].append(alias)
                id_start += 1
        ntype = self.node_instance_type
        nimage = self.node_image_id
        if not (ntype, nimage) in lmap:
            lmap[(ntype, nimage)] = []
        for id in range(id_start, self.cluster_size):
            alias = self._make_alias(id)
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
        log.info("Launching a %d-node %s" % (self.cluster_size, ' '.join(
            ['VPC' if self.subnet_ids else '', 'cluster...']).strip()))
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
        insts = []
        master_alias = self._make_alias(master=True)
        itype, image = [i for i in lmap if master_alias in lmap[i]][0]
        aliases = lmap.get((itype, image))
        for alias in aliases:
            log.debug("Launching %s (ami: %s, type: %s)" %
                      (alias, image, itype))
        master_response = self.create_nodes(aliases, image_id=image,
                                            instance_type=itype,
                                            force_flat=True)[0]
        zone = master_response.instances[0].placement
        insts.extend(master_response.instances)
        lmap.pop((itype, image))
        for (itype, image) in lmap:
            aliases = lmap.get((itype, image))
            if not aliases:
                continue
            for alias in aliases:
                log.debug("Launching %s (ami: %s, type: %s)" %
                          (alias, image, itype))
            resv = self.create_nodes(aliases, image_id=image,
                                     instance_type=itype, zone=zone,
                                     force_flat=True)
            insts.extend(resv[0].instances)
        self.ec2.wait_for_propagation(instances=insts)

    def _create_spot_cluster(self):
        """
        Launches cluster using spot instances for all worker nodes. This method
        makes a single spot request for each node in the cluster since spot
        instances *always* have an ami_launch_index of 0. This is needed in
        order to correctly assign aliases to nodes.
        """
        master_alias = self._make_alias(master=True)
        (mtype, mimage) = self._get_type_and_image_id(master_alias)
        log.info("Launching master node (ami: %s, type: %s)..." %
                 (mimage, mtype))
        force_flat = not self.force_spot_master
        master_response = self.create_node(master_alias,
                                           image_id=mimage,
                                           instance_type=mtype,
                                           force_flat=force_flat)
        insts, spot_reqs = [], []
        zone = None
        if not force_flat and self.spot_bid:
            # Make sure nodes are in same zone as master
            launch_spec = master_response.launch_specification
            zone = launch_spec.placement
            spot_reqs.append(master_response)
        else:
            # Make sure nodes are in same zone as master
            zone = master_response.instances[0].placement
            insts.extend(master_response.instances)
        for id in range(1, self.cluster_size):
            alias = self._make_alias(id)
            (ntype, nimage) = self._get_type_and_image_id(alias)
            log.info("Launching %s (ami: %s, type: %s)" %
                     (alias, nimage, ntype))
            spot_req = self.create_node(alias, image_id=nimage,
                                        instance_type=ntype, zone=zone)
            spot_reqs.append(spot_req)
        self.ec2.wait_for_propagation(instances=insts, spot_requests=spot_reqs)

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

    @property
    def pool(self):
        if not self._pool:
            self._pool = threadpool.get_thread_pool(
                size=self.num_threads, disable_threads=self.disable_threads)
        return self._pool

    @property
    def validator(self):
        return ClusterValidator(self)

    def is_valid(self):
        return self.validator.is_valid()

    def validate(self):
        return self.validator.validate()

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
                active_spots = [s for s in spots if s.state == "active" and
                                s.instance_id]
                pbar.maxval = len(spots)
                pbar.update(len(active_spots))
                if not pbar.finished:
                    time.sleep(self.refresh_interval)
                    spots = self.get_spot_requests_or_raise(spots)
            pbar.reset()
        self.ec2.wait_for_propagation(
            instances=[s.instance_id for s in spots])

    def wait_for_running_instances(self, nodes=None,
                                   kill_pending_after_mins=15):
        """
        Wait until all cluster nodes are in a 'running' state
        """
        log.info("Waiting for all nodes to be in a 'running' state...")
        _nodes = nodes or self.get_nodes_or_raise()
        pbar = self.progress_bar.reset()
        pbar.maxval = len(_nodes)
        pbar.update(0)
        now = utils.get_utc_now()
        timeout = now + datetime.timedelta(minutes=kill_pending_after_mins)
        while not pbar.finished:
            running_nodes = [n for n in _nodes if n.state == "running"]
            pbar.maxval = len(_nodes)
            pbar.update(len(running_nodes))
            if not pbar.finished:
                if utils.get_utc_now() > timeout:
                    pending = [n for n in _nodes if n not in running_nodes]
                    log.warn("%d nodes have been pending for >= %d mins "
                             "- terminating" % (len(pending),
                                                kill_pending_after_mins))
                    for node in pending:
                        node.terminate()
                else:
                    time.sleep(self.refresh_interval)
                _nodes = self.get_nodes_or_raise(nodes)
        pbar.reset()

    def wait_for_ssh(self, nodes=None, reboot_interval=10,
                     n_reboot_restart=False):
        """
        Wait until all cluster nodes are in a 'running' state
        """
        log.info("Waiting for SSH to come up on all nodes...")
        nodes = nodes or self.get_nodes_or_raise()
        params = {"interval": self.refresh_interval,
                  "reboot_interval": reboot_interval,
                  "n_reboot_restart": n_reboot_restart}
        self.pool.map(
            lambda n: n.wait(**params),
            nodes,
            jobid_fn=lambda n: n.alias)

    @print_timing("Waiting for cluster to come up")
    def wait_for_cluster(self, msg="Waiting for cluster to come up...",
                         reboot_interval=10, n_reboot_restart=False):
        """
        Wait for cluster to come up and display progress bar. Waits for all
        spot requests to become 'active', all instances to be in a 'running'
        state, and for all SSH daemons to come up.

        msg - custom message to print out before waiting on the cluster
        """
        interval = self.refresh_interval
        log.info("%s %s" % (msg, "(updating every %ds)" % interval))
        try:
            self.wait_for_active_spots()
            self.wait_for_running_instances()
            self.wait_for_ssh(reboot_interval=reboot_interval,
                              n_reboot_restart=n_reboot_restart)
        except Exception:
            self.progress_bar.finish()
            raise

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
        filters = {'instance.group-name': self._security_group,
                   'instance-state-name': states}
        insts = self.ec2.get_all_instances(filters=filters)
        return len(insts) == 0

    def attach_volumes_to_master(self):
        """
        Attach each volume to the master node
        """
        wait_for_volumes = []
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
            log.info("Attaching volume %s to master node on %s ..." %
                     (vol.id, device))
            resp = vol.attach(self.master_node.id, device)
            log.debug("resp = %s" % resp)
            wait_for_volumes.append(vol)
        for vol in wait_for_volumes:
            self.ec2.wait_for_volume(vol, state='attached')

    def detach_volumes(self):
        """
        Detach all volumes from all nodes
        """
        for node in self.nodes:
            node.detach_external_volumes()

    @print_timing('Restarting cluster')
    def restart_cluster(self, reboot_only=False):
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
        if reboot_only:
            return
        sleep = 20
        log.info("Sleeping for %d seconds..." % sleep)
        time.sleep(sleep)
        self.setup_cluster(False)

    def stop_cluster(self, terminate_unstoppable=False, force=False):
        """
        Shutdown this cluster by detaching all volumes and 'stopping' all nodes

        In general, all nodes in the cluster must be 'stoppable' meaning all
        nodes are backed by flat-rate EBS-backed instances. If any
        'unstoppable' nodes are found an exception is raised. A node is
        'unstoppable' if it is backed by either a spot or S3-backed instance.

        If the cluster contains a mix of 'stoppable' and 'unstoppable' nodes
        you can stop all stoppable nodes and terminate any unstoppable nodes by
        setting terminate_unstoppable=True.
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
        except exception.MasterDoesNotExist as e:
            if force:
                log.warn("Cannot run plugins: %s" % e)
            else:
                raise
        self.detach_volumes()
        for node in nodes:
            node.shutdown()

    def terminate_cluster(self, force=False):
        """
        Destroy this cluster by first detaching all volumes, shutting down all
        instances, canceling all spot requests (if any), removing its placement
        group (if any), and removing its security group.
        """
        try:
            self.run_plugins(method_name="on_shutdown", reverse=True)
        except exception.MasterDoesNotExist as e:
            if force:
                log.warn("Cannot run plugins: %s" % e)
            else:
                raise
        self.detach_volumes()
        nodes = self.nodes
        for node in nodes:
            node.terminate()
        for spot in self.spot_requests:
            if spot.state not in ['cancelled', 'closed']:
                log.info("Canceling spot instance request: %s" % spot.id)
                spot.cancel()
        s = utils.get_spinner("Waiting for cluster to terminate...")
        try:
            while not self.is_cluster_terminated():
                time.sleep(5)
        finally:
            s.stop()
        region = self.ec2.region.name
        if region in static.PLACEMENT_GROUP_REGIONS:
            pg = self.ec2.get_placement_group_or_none(self._security_group)
            if pg:
                self.ec2.delete_group(pg)
        sg = self.ec2.get_group_or_none(self._security_group)
        if sg:
            self.ec2.delete_group(sg)

    def start(self, create=True, create_only=False, validate=True,
              validate_only=False, validate_running=False,
              save_config_on_master=False):
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
            validator = self.validator
            if not create and validate_running:
                try:
                    validator.validate_running_instances()
                except exception.ClusterValidationError as e:
                    msg = "Existing nodes are not compatible with cluster "
                    msg += "settings:\n"
                    e.msg = msg + e.msg
                    raise
            validator.validate()
            if validate_only:
                return
        else:
            log.warn("SKIPPING VALIDATION - USE AT YOUR OWN RISK")
        return self._start(create=create, create_only=create_only,
                           save_config_on_master=save_config_on_master)

    @print_timing("Starting cluster")
    def _start(self, create=True, create_only=False,
               save_config_on_master=False):
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
        self.setup_cluster(save_config_on_master)

    def setup_cluster(self, save_config_on_master):
        """
        Waits for all nodes to come up and then runs the default
        StarCluster setup routines followed by any additional plugin setup
        routines
        """
        self.wait_for_cluster()
        self._setup_cluster(save_config_on_master)

    @print_timing("Configuring cluster")
    def _setup_cluster(self, save_config_on_master):
        """
        Runs the default StarCluster setup routines followed by any additional
        plugin setup routines. Does not wait for nodes to come up.
        """
        log.info("The master node is %s" % self.master_node.dns_name)
        log.info("Configuring cluster...")
        if save_config_on_master:
            self.save_config_on_master()
        if self.volumes:
            self.attach_volumes_to_master()
        self.run_plugins()

    def run_plugins(self, plugins=None, method_name="run", node=None,
                    reverse=False, nodes=None):
        """
        Run all plugins specified in this Cluster object's self.plugins list
        Uses plugins list instead of self.plugins if specified.

        plugins must be a tuple: the first element is the plugin's name, the
        second element is the plugin object (a subclass of ClusterSetup)
        """
        plugs = [self._default_plugin]
        if not self.disable_queue:
            plugs.append(self._sge_plugin)
        _plugs = plugins or self.plugins
        if _plugs:
            plugs += _plugs[:]
        if reverse:
            plugs.reverse()
        for plug in plugs:
            self.run_plugin(plug, method_name=method_name, node=node,
                            nodes=nodes)

    def run_plugin(self, plugin, name='', method_name='run', node=None,
                   nodes=None, args=None):
        """
        Run a StarCluster plugin.

        plugin - an instance of the plugin's class
        name - a user-friendly label for the plugin
        method_name - the method to run within the plugin (default: "run")
        node - optional node to pass as first argument to plugin method (used
        for on_add_node/on_remove_node)
        """
        if args is None:
            args = []
        plugin_name = name or getattr(plugin, '__name__',
                                      utils.get_fq_class_name(plugin))
        try:
            func = getattr(plugin, method_name, None)
            if not func:
                log.warn("Plugin %s has no %s method...skipping" %
                         (plugin_name, method_name))
                return
            args = [nodes or self.nodes, self.master_node, self.cluster_user,
                    self.cluster_shell, self.volumes] + args
            if node:
                args.insert(0, node)
            log.info("Running plugin %s" % plugin_name)
            func(*args)
        except NotImplementedError:
            log.debug("method %s not implemented by plugin %s" % (method_name,
                                                                  plugin_name))
        except exception.MasterDoesNotExist:
            raise
        except KeyboardInterrupt:
            raise
        except Exception:
            import traceback
            log.debug(traceback.format_exc())
            log.error("Error occured while running plugin '%s':" % plugin_name)
            raise

    def ssh_to_master(self, user='root', command=None, forward_x11=False,
                      forward_agent=False, pseudo_tty=False):
        return self.master_node.shell(user=user, command=command,
                                      forward_x11=forward_x11,
                                      forward_agent=forward_agent,
                                      pseudo_tty=pseudo_tty)

    def ssh_to_node(self, alias, user='root', command=None, forward_x11=False,
                    forward_agent=False, pseudo_tty=False):
        node = self.get_node(alias)
        return node.shell(user=user, forward_x11=forward_x11,
                          forward_agent=forward_agent,
                          pseudo_tty=pseudo_tty,
                          command=command)

    def get_impaired_nodes(self):
        impaired_statuses = []
        node_ids = [node.id for node in self.nodes]
        for instance_id_batch in utils.chunk_list(node_ids, 100):
            impaired_statuses.extend(self.ec2.conn.get_all_instance_status(
                instance_ids=instance_id_batch,
                filters={"instance-status.status": "impaired"}
            ))
        impaired_nodes_ids = [impaired.id for impaired in impaired_statuses]
        return [node for node in self.nodes if node.id in impaired_nodes_ids]

    def clean_impaired(self):
        impaired_nodes = self.get_impaired_nodes()
        previously_impaired_nodes = self._impaired_nodes
        now = utils.get_utc_now()
        self._impaired_nodes = {}

        for node in impaired_nodes:
            # set _impaired_nodes dict as if everything was since now
            self._impaired_nodes[node.alias] = {
                'since': now,
                'node': node
            }

        if not self._impaired_nodes:
            # nothing to do
            return

        configurable_threshold = self._impaired_threshold_sec
        threshold = now - datetime.timedelta(seconds=configurable_threshold)
        for alias, data in self._impaired_nodes.iteritems():
            if alias in previously_impaired_nodes:
                # if the node was already impaired, update _impaired_nodes
                data['since'] = previously_impaired_nodes[alias]['since']
            log.info("Node {node.alias} impaired since {since}".format(**data))

            # if is impaired for longer than threshold, handle it
            if data['since'] <= threshold:
                msg = "Handling node {}, impaired since {}, longer than " \
                      "configured threshold of {} seconds" \
                      .format(alias, data['since'], configurable_threshold)
                log.warn(msg)

                if data['node'].is_master():
                    log.error("Master appears to be impaired but will not "
                              "be handled")
                    continue

                data['node'].handle_irresponsive_node()

    def clean(self):
        self.clean_impaired()

        if not self.disable_queue:
            # clean sge
            sge_plugin = sge.SGEPlugin()
            sge_plugin.clean_cluster(self.nodes, self.master_node,
                                     self.cluster_user,
                                     self.cluster_shell, self.volumes)

        self.run_plugins(method_name="clean_cluster", reverse=True)

    def _recover_duplicate_aliases(self):
        aliases = self._get_duplicate_aliases()
        if not aliases:
            return

        log.error("Nodes with same alias detected! {}".format(aliases))
        etc_hosts = self._master.ssh.get_remote_file_lines('/etc/hosts')
        for alias in aliases:
            ip = None
            for line in etc_hosts:
                if re.findall(alias, line):
                    ip, _ = line.split(" ", 1)
                    log.debug("Found ip: " + ip)
                    break
            else:
                log.debug("No ip found")
            for node in self.nodes:
                if node.alias != alias:
                    continue
                if node.private_ip_address != ip:
                    new_alias = self._make_alias(
                        self._get_free_node_nums(1)[0])
                    log.info("Renaming {} from {} to {}"
                             .format(node, node.alias, new_alias))
                    node.rename(new_alias)
                    # force a memory refresh
                    self._nodes = []
                    self.nodes

    def recover(self, reboot_interval=10, n_reboot_restart=False):
        """
        Will try to recover dangling nodes.
        remove_on_error The hour block minute after wich termination is
            authorised. False means it will never be terminated. True is
            equivalent to setting 0, meaning that it will only try to add
            it back once before terminating.
        """
        self._recover_duplicate_aliases()
        self.run_plugins(method_name="recover", reverse=True)
        sirs = filter(lambda sir: sir.state == "open", self.spot_requests)
        if sirs:
            streaming_add(self, spots=sirs, reboot_interval=reboot_interval,
                          n_reboot_restart=n_reboot_restart)

        to_recover = []
        if not self.disable_queue:
            sge_plugin = sge.SGEPlugin()
            to_recover.append(sge_plugin.get_nodes_to_recover(self.nodes))
        for plugin in self.plugins:
            if hasattr(plugin, "get_nodes_to_recover"):
                result = plugin.get_nodes_to_recover(self.nodes)
                to_recover.append(result)
        if len(to_recover) > 1:
            log.error("Support for more than one list of nodes "
                      "to recover is not implemented")
        elif len(to_recover) == 1 and len(to_recover[0]) > 0:
            streaming_add(self, instances=to_recover[0],
                          reboot_interval=reboot_interval,
                          n_reboot_restart=n_reboot_restart)
        log.info("Out of recover procedure")


class ClusterValidator(validators.Validator):

    """
    Validates that cluster settings define a sane launch configuration.
    Throws exception.ClusterValidationError for all validation failures
    """
    def __init__(self, cluster):
        self.cluster = cluster

    def is_running_valid(self):
        """
        Checks whether the current running instances are compatible
        with this cluster template's settings
        """
        try:
            self.validate_running_instances()
            return True
        except exception.ClusterValidationError as e:
            log.error(e.msg)
            return False

    def validate_required_settings(self):
        has_all_required = True
        for opt in static.CLUSTER_SETTINGS:
            requirements = static.CLUSTER_SETTINGS[opt]
            name = opt
            required = requirements[1]
            if required and self.cluster.get(name.lower()) is None:
                log.warn('Missing required setting %s' % name)
                has_all_required = False
        return has_all_required

    def validate_running_instances(self):
        """
        Validate existing instances against this cluster's settings
        """
        cluster = self.cluster
        cluster.wait_for_active_spots()
        nodes = cluster.nodes
        if not nodes:
            raise exception.ClusterValidationError("No existing nodes found!")
        log.info("Validating existing instances...")
        mazone = cluster.master_node.placement
        # reset zone cache
        cluster._zone = None
        if cluster.zone and cluster.zone.name != mazone:
            raise exception.ClusterValidationError(
                "Running cluster's availability_zone (%s) != %s" %
                (mazone, cluster.zone.name))
        for node in nodes:
            if node.key_name != cluster.keyname:
                raise exception.ClusterValidationError(
                    "%s's key_name (%s) != %s" % (node.alias, node.key_name,
                                                  cluster.keyname))

    def validate(self):
        """
        Checks that all cluster template settings are valid and raises an
        exception.ClusterValidationError exception if not.
        """
        log.info("Validating cluster template settings...")
        try:
            self.validate_required_settings()
            self.validate_vpc()
            self.validate_dns_prefix()
            self.validate_dns_suffix()
            self.validate_spot_bid()
            self.validate_cluster_size()
            self.validate_cluster_user()
            self.validate_shell_setting()
            self.validate_permission_settings()
            self.validate_credentials()
            self.validate_keypair()
            self.validate_zone()
            self.validate_ebs_settings()
            self.validate_ebs_aws_settings()
            self.validate_image_settings()
            self.validate_instance_types()
            self.validate_userdata()
            log.info('Cluster template settings are valid')
            return True
        except exception.ClusterValidationError as e:
            e.msg = 'Cluster settings are not valid:\n%s' % e.msg
            raise

    def is_valid(self):
        """
        Returns True if all cluster template settings are valid
        """
        try:
            self.validate()
            return True
        except exception.ClusterValidationError as e:
            log.error(e.msg)
            return False

    def validate_dns_prefix(self):
        if not self.cluster.dns_prefix:
            return True

        # check that the dns prefix is a valid hostname
        is_valid = utils.is_valid_hostname(self.cluster.dns_prefix)
        if not is_valid:
            raise exception.ClusterValidationError(
                "The cluster name you chose, {dns_prefix}, is"
                " not a valid dns name. "
                " Since you have chosen to prepend the hostnames"
                " via the dns_prefix option, {dns_prefix} should only have"
                " alphanumeric characters and a '-' or '.'".format(
                    dns_prefix=self.cluster.dns_prefix))
        return True

    def validate_dns_suffix(self):
        if not self.cluster.dns_suffix:
            return True

        # check that the dns prefix is a valid hostname
        is_valid = utils.is_valid_hostname(self.cluster.dns_suffix)
        if not is_valid:
            raise exception.ClusterValidationError(
                "The cluster name you chose, {dns_suffix}, is"
                " not a valid dns name. "
                " Since you have chosen to append to the hostnames"
                " via the dns_suffix option, {dns_suffix} should only have"
                " alphanumeric characters and a '-' or '.'".format(
                    dns_suffix=self.cluster.dns_suffix))
        return True

    def validate_spot_bid(self):
        cluster = self.cluster
        if cluster.spot_bid is not None:
            for i in cluster.node_instance_array:
                spot_bid = i.get('spot_bid', None)
                if spot_bid is None:
                    raise exception.ClusterValidationError(
                        'Either all or no nodes must specify a spot_bid.')
                if type(spot_bid) not in [int, float]:
                    raise exception.ClusterValidationError(
                        'spot_bid must be integer or float')
                if spot_bid <= 0:
                    raise exception.ClusterValidationError(
                        'spot_bid must be an integer or float > 0')
        else:
            for i in cluster.node_instance_array:
                spot_bid = i.get('spot_bid', None)
                if spot_bid is not None:
                    raise exception.ClusterValidationError(
                        'Either all or no nodes must specify a spot_bid.')
        return True

    def validate_cluster_size(self):
        cluster = self.cluster
        try:
            int(cluster.cluster_size)
            if cluster.cluster_size < 1:
                raise ValueError
        except (ValueError, TypeError):
            raise exception.ClusterValidationError(
                'cluster_size must be an integer >= 1')
        num_itypes = sum([i.get('size', 0) for i in
                          cluster.node_instance_array])
        num_nodes = cluster.cluster_size - 1
        if num_itypes > num_nodes:
            raise exception.ClusterValidationError(
                "total number of nodes specified in node_instance_type (%s) "
                "must be <= cluster_size-1 (%s)" % (num_itypes, num_nodes))
        return True

    def validate_cluster_user(self):
        if self.cluster.cluster_user == "root":
            raise exception.ClusterValidationError(
                'cluster_user cannot be "root"')
        return True

    def validate_shell_setting(self):
        cluster_shell = self.cluster.cluster_shell
        if not static.AVAILABLE_SHELLS.get(cluster_shell):
            raise exception.ClusterValidationError(
                'Invalid user shell specified. Options are %s' %
                ' '.join(static.AVAILABLE_SHELLS.keys()))
        return True

    def _check_image_available(self, image_id, name):
        image = self.cluster.ec2.get_image_or_none(image_id)
        if not image or image.id != image_id:
            raise exception.ClusterValidationError(
                '%s %s does not exist' % (name, image_id))
        if image.state != 'available':
            raise exception.ClusterValidationError(
                '%s %s is not available' % (name, image_id))

    def validate_image_settings(self):
        cluster = self.cluster
        master_image_id = cluster.master_image_id
        if master_image_id:
            self._check_image_available(master_image_id, 'master_image_id')
        node_instance_array = cluster.node_instance_array
        image_ids = {item['image_id'] for item in node_instance_array}
        for image_id in image_ids:
            self._check_image_available(image_id, 'node_image_id')
        return True

    def validate_zone(self):
        """
        Validates that the cluster's availability zone exists and is available.
        The 'zone' property additionally checks that all EBS volumes are in the
        same zone and that the cluster's availability zone setting, if
        specified, matches the EBS volume(s) zone.
        """
        zone = self.cluster.zone
        if zone and zone.state != 'available':
            raise exception.ClusterValidationError(
                "The '%s' availability zone is not available at this time" %
                zone.name)
        return True

    def __check_platform(self, image_id, instance_type):
        """
        Validates whether an image_id (AMI) is compatible with a given
        instance_type. image_id_setting and instance_type_setting are the
        setting labels in the config file.
        """
        image = self.cluster.ec2.get_image_or_none(image_id)
        if not image:
            raise exception.ClusterValidationError('Image %s does not exist' %
                                                   image_id)
        image_platform = image.architecture
        image_is_hvm = (image.virtualization_type == "hvm")
        if image_is_hvm and instance_type not in static.HVM_TYPES:
            cctypes_list = ', '.join(static.HVM_TYPES)
            raise exception.ClusterValidationError(
                "Image '%s' is a hardware virtual machine (HVM) image and "
                "cannot be used with instance type '%s'.\n\nHVM images "
                "require one of the following HVM instance types:\n%s" %
                (image_id, instance_type, cctypes_list))
        if instance_type in static.HVM_ONLY_TYPES and not image_is_hvm:
            raise exception.ClusterValidationError(
                "The '%s' instance type can only be used with hardware "
                "virtual machine (HVM) images. Image '%s' is not an HVM "
                "image." % (instance_type, image_id))
        instance_platforms = static.INSTANCE_TYPES[instance_type]
        if image_platform not in instance_platforms:
            error_msg = "Instance type %(instance_type)s is for an " \
                        "%(instance_platform)s platform while " \
                        "%(image_id)s is an %(image_platform)s platform"
            error_dict = {'instance_type': instance_type,
                          'instance_platform': ', '.join(instance_platforms),
                          'image_id': image_id,
                          'image_platform': image_platform}
            raise exception.ClusterValidationError(error_msg % error_dict)
        image_is_ebs = (image.root_device_type == 'ebs')
        if instance_type in static.EBS_ONLY_TYPES and not image_is_ebs:
            error_msg = ("Instance type %s can only be used with an "
                         "EBS-backed AMI and '%s' is not EBS-backed " %
                         (instance_type, image.id))
            raise exception.ClusterValidationError(error_msg)
        return True

    def _check_instance_type(self, instance_type, name):
        instance_types = static.INSTANCE_TYPES
        if instance_type not in instance_types:
            instance_type_list = ', '.join(instance_types.keys())
            raise exception.ClusterValidationError(
                "You specified an invalid %s %s\n"
                "Possible options are:\n%s" %
                (name, instance_type, instance_type_list))

    def _check_platform(self, image_id_pair, instance_type_pair):
        try:
            self.__check_platform(image_id_pair[1], instance_type_pair[1])
        except exception.ClusterValidationError as e:
            raise exception.ClusterValidationError(
                'Incompatible %s and %s:\n%s' % (image_id_pair[0],
                                                 instance_type_pair[0], e.msg))

    def validate_instance_types(self):
        cluster = self.cluster
        master_image_id = cluster.master_image_id
        node_image_id = cluster.node_image_id
        master_instance_type = cluster.master_instance_type
        node_instance_type = cluster.node_instance_type
        if master_instance_type:
            self._check_instance_type(master_instance_type,
                                      'master_instance_type')
        node_instance_array = cluster.node_instance_array
        instance_types = \
            [item['instance_type'] for item in node_instance_array]
        image_ids = [item['image_id'] for item in node_instance_array]
        for instance_type, image_id in zip(instance_types, image_ids):
            self._check_instance_type(instance_type, 'instance_type')
            self._check_platform(('node_image_id', image_id),
                                 ('node_instance_type', instance_type))
        if master_image_id and not master_instance_type:
            self._check_platform(('master_image_id', master_image_id),
                                 ('node_instance_type', node_instance_type))
        elif master_image_id and master_instance_type:
            self._check_platform(
                ('master_image_id', master_image_id),
                ('master_instance_type', master_instance_type))
        elif master_instance_type and not master_image_id:
            self._check_platform(
                ('node_image_id', node_image_id),
                ('master_instance_type', master_instance_type))
        return True

    def validate_permission_settings(self):
        permissions = self.cluster.permissions
        for perm in permissions:
            permission = permissions.get(perm)
            protocol = permission.get('ip_protocol')
            if protocol not in static.PROTOCOLS:
                raise exception.InvalidProtocol(protocol)
            from_port = permission.get('from_port')
            to_port = permission.get('to_port')
            try:
                from_port = int(from_port)
                to_port = int(to_port)
            except ValueError:
                raise exception.InvalidPortRange(
                    from_port, to_port, reason="integer range required")
            if protocol == 'icmp':
                if from_port != -1 or to_port != -1:
                    raise exception.InvalidPortRange(
                        from_port, to_port,
                        reason="for icmp protocol from_port "
                        "and to_port must be -1")
            else:
                if from_port < 0 or to_port < 0:
                    raise exception.InvalidPortRange(
                        from_port, to_port,
                        reason="from/to must be positive integers")
                if from_port > to_port:
                    raise exception.InvalidPortRange(
                        from_port, to_port,
                        reason="'from_port' must be <= 'to_port'")
            cidr_ip = permission.get('cidr_ip')
            if not iptools.ipv4.validate_cidr(cidr_ip):
                raise exception.InvalidCIDRSpecified(cidr_ip)

    def validate_ebs_settings(self):
        """
        Check EBS vols for missing/duplicate DEVICE/PARTITION/MOUNT_PATHs and
        validate these settings.
        """
        volmap = {}
        devmap = {}
        mount_paths = []
        cluster = self.cluster
        for vol in cluster.volumes:
            vol_name = vol
            vol = cluster.volumes.get(vol)
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
            if mount_path == "/":
                raise exception.ClusterValidationError(
                    "MOUNT_PATH for volume %s cannot be /" % vol_name)
        for path in mount_paths:
            if mount_paths.count(path) > 1:
                raise exception.ClusterValidationError(
                    "Can't mount more than one volume on %s" % path)
        return True

    def validate_ebs_aws_settings(self):
        """
        Verify that all EBS volumes exist and are available.
        """
        cluster = self.cluster
        for vol in cluster.volumes:
            v = cluster.volumes.get(vol)
            vol_id = v.get('volume_id')
            vol = cluster.ec2.get_volume(vol_id)
            if vol.status != 'available':
                try:
                    if vol.attach_data.instance_id == cluster.master_node.id:
                        continue
                except exception.MasterDoesNotExist:
                    pass
                raise exception.ClusterValidationError(
                    "Volume '%s' is not available (status: %s)" %
                    (vol_id, vol.status))

    def validate_credentials(self):
        if not self.cluster.ec2.is_valid_conn():
            raise exception.ClusterValidationError(
                'Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination.')
        return True

    def validate_keypair(self):
        cluster = self.cluster
        key_location = cluster.key_location
        if not key_location:
            raise exception.ClusterValidationError(
                "no key_location specified for key '%s'" %
                cluster.keyname)
        if not os.path.exists(key_location):
            raise exception.ClusterValidationError(
                "key_location '%s' does not exist" % key_location)
        elif not os.path.isfile(key_location):
            raise exception.ClusterValidationError(
                "key_location '%s' is not a file" % key_location)
        keyname = cluster.keyname
        keypair = cluster.ec2.get_keypair_or_none(keyname)
        if not keypair:
            raise exception.ClusterValidationError(
                "Keypair '%s' does not exist in region '%s'" %
                (keyname, cluster.ec2.region.name))
        fingerprint = keypair.fingerprint
        try:
            open(key_location, 'r').close()
        except IOError as e:
            raise exception.ClusterValidationError(
                "Error loading key_location '%s':\n%s\n"
                "Please check that the file is readable" % (key_location, e))
        if len(fingerprint) == 59:
            keyfingerprint = sshutils.get_private_rsa_fingerprint(key_location)
        elif len(fingerprint) == 47:
            keyfingerprint = sshutils.get_public_rsa_fingerprint(key_location)
        else:
            raise exception.ClusterValidationError(
                "Unrecognized fingerprint for %s: %s" % (keyname, fingerprint))
        if keyfingerprint != fingerprint:
            raise exception.ClusterValidationError(
                "Incorrect fingerprint for key_location '%s'\n\n"
                "local fingerprint: %s\n\nkeypair fingerprint: %s"
                % (key_location, keyfingerprint, fingerprint))
        return True

    def validate_userdata(self):
        for script in self.cluster.userdata_scripts:
            if not os.path.exists(script):
                raise exception.ClusterValidationError(
                    "Userdata script does not exist: %s" % script)
            if not os.path.isfile(script):
                raise exception.ClusterValidationError(
                    "Userdata script is not a file: %s" % script)
        if self.cluster.spot_bid is None:
            lmap = self.cluster._get_launch_map()
            aliases = max(lmap.values(), key=lambda x: len(x))
            ud = self.cluster._get_cluster_userdata(aliases)
        else:
            ud = self.cluster._get_cluster_userdata(
                [self.cluster._make_alias(id=1)])
        ud_size_kb = utils.size_in_kb(ud)
        if ud_size_kb > 16:
            raise exception.ClusterValidationError(
                "User data is too big! (%.2fKB)\n"
                "User data scripts combined and compressed must be <= 16KB\n"
                "NOTE: StarCluster uses anywhere from 0.5-2KB "
                "to store internal metadata" % ud_size_kb)

    def validate_vpc(self):
        if not self.cluster.subnet_ids:
            return
        if self.cluster.public_ips is False:
            raise exception.ClusterValidationError(
                "Only VPC clusters can disable public IP addresses")

        try:
            assert self.cluster.vpc_id is not None
        except exception.SubnetDoesNotExist as e:
            raise exception.ClusterValidationError(e)

        azone = self.cluster.availability_zone
        if len(self.cluster.subnet_ids) > 1 and azone:
            raise exception.ClusterValidationError(
                "Cannot define a cluster availability_zone with multiple "
                "subnets at the same time.")

        nodes = self.cluster.nodes
        zones = []
        for subnet_id in self.cluster.subnet_ids:
            subnet = self.cluster.ec2.get_subnet(subnet_id)

            if subnet is None:
                raise exception.ClusterValidationError(
                    "Subnet id {} not found".format(subnet_id))
            vpc_id = self.cluster.get_vpc_id(subnet_id)
            assert vpc_id is not None
            if vpc_id != self.cluster.vpc_id:
                raise exception.ClusterValidationError(
                    "All subnets must be in the same vpc")
            szone = subnet.availability_zone
            zones.append(szone)
            if azone and szone != azone:
                raise exception.ClusterValidationError(
                    "The cluster availability_zone (%s) does not match "
                    "the subnet zone (%s)" % (azone, szone))

            ip_count = subnet.available_ip_address_count
            if not nodes and ip_count < self.cluster.cluster_size:
                raise exception.ClusterValidationError(
                    "Not enough IP addresses available in %s (%d)" %
                    (self.cluster.subnet.id, ip_count))

        zones_count = Counter(zones)
        for zone, count in zones_count.iteritems():
            if count > 1:
                raise exception.ClusterValidationError(
                    "You cannot define 2 or more subnets in the same zone. "
                    "({})".format(zone))

        if self.cluster.public_ips:
            gws = self.cluster.ec2.get_internet_gateways(filters={
                'attachment.vpc-id': self.cluster.vpc_id})
            if not gws:
                raise exception.ClusterValidationError(
                    "No internet gateway attached to VPC: %s" %
                    self.cluster.vpc_id)
            # for subnet_id in self.cluster.subnet_ids:
            #     rtables = self.cluster.ec2.get_route_tables(filters={
            #         'association.subnet-id': subnet_id,
            #         'route.destination-cidr-block': static.WORLD_CIDRIP,
            #         'route.gateway-id': gws[0].id})
            #     if not rtables:
            #         raise exception.ClusterValidationError(
            #             "No route to %s found for subnet: %s" %
            #             (static.WORLD_CIDRIP, subnet_id))
        else:
            log.warn(user_msgs.public_ips_disabled %
                     dict(vpc_id=self.cluster.vpc_id))


if __name__ == "__main__":
    from starcluster.config import StarClusterConfig
    cfg = StarClusterConfig().load()
    sc = cfg.get_cluster_template('smallcluster', 'mynewcluster')
    if sc.is_valid():
        sc.start(create=True)
