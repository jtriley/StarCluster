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

"""
EC2/S3 Utility Classes
"""

import os
import re
import time
import base64
import string
import tempfile

import boto
import boto.ec2
import boto.s3.connection
from boto import config as boto_config
from boto.connection import HAVE_HTTPS_CONNECTION

from starcluster import image
from starcluster import utils
from starcluster import static
from starcluster import spinner
from starcluster import sshutils
from starcluster import webtools
from starcluster import exception
from starcluster import progressbar
from starcluster.utils import print_timing
from starcluster.logger import log


class EasyAWS(object):
    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 connection_authenticator, **kwargs):
        """
        Create an EasyAWS object.

        Requires aws_access_key_id/aws_secret_access_key from an Amazon Web
        Services (AWS) account and a connection_authenticator function that
        returns an authenticated AWS connection object

        Providing only the keys will default to using Amazon EC2

        kwargs are passed to the connection_authenticator's constructor
        """
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.connection_authenticator = connection_authenticator
        self._conn = None
        self._kwargs = kwargs

    def reload(self):
        self._conn = None
        return self.conn

    @property
    def conn(self):
        if self._conn is None:
            log.debug('creating self._conn w/ connection_authenticator ' +
                      'kwargs = %s' % self._kwargs)
            validate_certs = self._kwargs.get('validate_certs', True)
            if validate_certs:
                if not HAVE_HTTPS_CONNECTION:
                    raise exception.AWSError(
                        "Failed to validate AWS SSL certificates. "
                        "SSL certificate validation is only supported "
                        "on Python>=2.6.\n\nSet AWS_VALIDATE_CERTS=False in "
                        "the [aws info] section of your config to skip SSL "
                        "certificate verification and suppress this error AT "
                        "YOUR OWN RISK.")
            if not boto_config.has_section('Boto'):
                boto_config.add_section('Boto')
            # Hack to get around the fact that boto ignores validate_certs
            # if https_validate_certificates is declared in the boto config
            boto_config.setbool('Boto', 'https_validate_certificates',
                                validate_certs)
            self._conn = self.connection_authenticator(
                self.aws_access_key_id, self.aws_secret_access_key,
                **self._kwargs)
            self._conn.https_validate_certificates = validate_certs
        return self._conn


class EasyEC2(EasyAWS):
    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 aws_ec2_path='/', aws_s3_host=None, aws_s3_path='/',
                 aws_port=None, aws_region_name=None, aws_is_secure=True,
                 aws_region_host=None, aws_proxy=None, aws_proxy_port=None,
                 aws_proxy_user=None, aws_proxy_pass=None,
                 aws_validate_certs=True, **kwargs):
        aws_region = None
        if aws_region_name and aws_region_host:
            aws_region = boto.ec2.regioninfo.RegionInfo(
                name=aws_region_name, endpoint=aws_region_host)
        kwds = dict(is_secure=aws_is_secure, region=aws_region, port=aws_port,
                    path=aws_ec2_path, proxy=aws_proxy,
                    proxy_port=aws_proxy_port, proxy_user=aws_proxy_user,
                    proxy_pass=aws_proxy_pass,
                    validate_certs=aws_validate_certs)
        super(EasyEC2, self).__init__(aws_access_key_id, aws_secret_access_key,
                                      boto.connect_vpc, **kwds)
        self._conn = kwargs.get('connection')
        kwds = dict(aws_s3_host=aws_s3_host, aws_s3_path=aws_s3_path,
                    aws_port=aws_port, aws_is_secure=aws_is_secure,
                    aws_proxy=aws_proxy, aws_proxy_port=aws_proxy_port,
                    aws_proxy_user=aws_proxy_user,
                    aws_proxy_pass=aws_proxy_pass,
                    aws_validate_certs=aws_validate_certs)
        self.s3 = EasyS3(aws_access_key_id, aws_secret_access_key, **kwds)
        self._regions = None
        self._account_attrs = None
        self._account_attrs_region = None

    def __repr__(self):
        return '<EasyEC2: %s (%s)>' % (self.region.name, self.region.endpoint)

    def _fetch_account_attrs(self):
        acct_attrs = self._account_attrs
        if not acct_attrs or self._account_attrs_region != self.region.name:
            resp = self.conn.describe_account_attributes(
                ['default-vpc', 'supported-platforms'])
            self._account_attrs = acct_attrs = {}
            for attr in resp:
                acct_attrs[attr.attribute_name] = attr.attribute_values
            self._account_attrs_region = self.region.name
        return self._account_attrs

    @property
    def supported_platforms(self):
        return self._fetch_account_attrs()['supported-platforms']

    @property
    def default_vpc(self):
        default_vpc = self._fetch_account_attrs()['default-vpc'][0]
        if default_vpc == 'none':
            default_vpc = None
        return default_vpc

    def connect_to_region(self, region_name):
        """
        Connects to a given region if it exists, raises RegionDoesNotExist
        otherwise. Once connected, this object will return only data from the
        given region.
        """
        region = self.get_region(region_name)
        self._kwargs['region'] = region
        self._platforms = None
        self._default_vpc = None
        self.reload()
        return self

    @property
    def region(self):
        """
        Returns the current EC2 region used by this EasyEC2 object
        """
        return self.conn.region

    @property
    def regions(self):
        """
        This property returns all AWS Regions, caching the results the first
        time a request is made to Amazon
        """
        if not self._regions:
            self._regions = {}
            regions = self.conn.get_all_regions()
            for region in regions:
                self._regions[region.name] = region
        return self._regions

    def get_region(self, region_name):
        """
        Returns boto Region object if it exists, raises RegionDoesNotExist
        otherwise.
        """
        if region_name not in self.regions:
            raise exception.RegionDoesNotExist(region_name)
        return self.regions.get(region_name)

    def list_regions(self):
        """
        Print name/endpoint for all AWS regions
        """
        regions = self.regions.items()
        regions.sort(reverse=True)
        for name, endpoint in regions:
            print 'name: ', name
            print 'endpoint: ', endpoint.endpoint
            print

    @property
    def registered_images(self):
        return self.conn.get_all_images(owners=["self"])

    @property
    def executable_images(self):
        return self.conn.get_all_images(executable_by=["self"])

    def get_registered_image(self, image_id):
        if not image_id.startswith('ami') or len(image_id) != 12:
            raise TypeError("invalid AMI name/id requested: %s" % image_id)
        for img in self.registered_images:
            if img.id == image_id:
                return img

    def _wait_for_group_deletion_propagation(self, group):
        if isinstance(group, boto.ec2.placementgroup.PlacementGroup):
            while self.get_placement_group_or_none(group.name):
                time.sleep(5)
        else:
            assert isinstance(group, boto.ec2.securitygroup.SecurityGroup)
            while self.get_group_or_none(group.name):
                time.sleep(5)

    def get_subnet(self, subnet_id):
        try:
            return self.get_subnets(filters={'subnet_id': subnet_id})[0]
        except IndexError:
            raise exception.SubnetDoesNotExist(subnet_id)

    def get_subnets(self, filters=None):
        return self.conn.get_all_subnets(filters=filters)

    def get_internet_gateways(self, filters=None):
        return self.conn.get_all_internet_gateways(filters=filters)

    def get_route_tables(self, filters=None):
        return self.conn.get_all_route_tables(filters=filters)

    def get_network_spec(self, *args, **kwargs):
        return boto.ec2.networkinterface.NetworkInterfaceSpecification(
            *args, **kwargs)

    def get_network_collection(self, *args, **kwargs):
        return boto.ec2.networkinterface.NetworkInterfaceCollection(
            *args, **kwargs)

    def delete_group(self, group, max_retries=60, retry_delay=5):
        """
        This method deletes a security or placement group using group.delete()
        but in the case that group.delete() throws a DependencyViolation error
        or InvalidPlacementGroup.InUse error it will keep retrying until it's
        successful. Waits 5 seconds between each retry.
        """
        label = 'security'
        if hasattr(group, 'strategy') and group.strategy == 'cluster':
            label = 'placement'
        s = utils.get_spinner("Removing %s group: %s" % (label, group.name))
        try:
            for i in range(max_retries):
                try:
                    ret_val = group.delete()
                    self._wait_for_group_deletion_propagation(group)
                    return ret_val
                except boto.exception.EC2ResponseError as e:
                    if i == max_retries - 1:
                        raise
                    if e.error_code == 'DependencyViolation':
                        log.debug('DependencyViolation error - retrying in 5s',
                                  exc_info=True)
                        time.sleep(retry_delay)
                    elif e.error_code == 'InvalidPlacementGroup.InUse':
                        log.debug('Placement group in use - retrying in 5s',
                                  exc_info=True)
                        time.sleep(retry_delay)
                    else:
                        raise
        finally:
            s.stop()

    def create_group(self, name, description, auth_ssh=False,
                     auth_group_traffic=False, vpc_id=None):
        """
        Create security group with name/description. auth_ssh=True
        will open port 22 to world (0.0.0.0/0). auth_group_traffic
        will allow all traffic between instances in the same security
        group
        """
        log.info("Creating security group %s..." % name)
        sg = self.conn.create_security_group(name, description, vpc_id=vpc_id)
        if not self.get_group_or_none(name):
            s = utils.get_spinner("Waiting for security group %s..." % name)
            try:
                while not self.get_group_or_none(name):
                    time.sleep(3)
            finally:
                s.stop()
        if auth_ssh:
            ssh_port = static.DEFAULT_SSH_PORT
            sg.authorize(ip_protocol='tcp', from_port=ssh_port,
                         to_port=ssh_port, cidr_ip=static.WORLD_CIDRIP)
        if auth_group_traffic:
            sg.authorize(src_group=sg, ip_protocol='icmp', from_port=-1,
                         to_port=-1)
            sg.authorize(src_group=sg, ip_protocol='tcp', from_port=1,
                         to_port=65535)
            sg.authorize(src_group=sg, ip_protocol='udp', from_port=1,
                         to_port=65535)
        return sg

    def get_all_security_groups(self, groupnames=[]):
        """
        Returns all security groups

        groupnames - optional list of group names to retrieve
        """
        filters = {}
        if groupnames:
            filters = {'group-name': groupnames}
        return self.get_security_groups(filters=filters)

    def get_group_or_none(self, name):
        """
        Returns group with name if it exists otherwise returns None
        """
        try:
            return self.get_security_group(name)
        except exception.SecurityGroupDoesNotExist:
            pass

    def get_or_create_group(self, name, description, auth_ssh=True,
                            auth_group_traffic=False, vpc_id=None):
        """
        Try to return a security group by name. If the group is not found,
        attempt to create it.  Description only applies to creation.

        auth_ssh - authorize ssh traffic from world
        auth_group_traffic - authorizes all traffic between members of the
                             group
        """
        sg = self.get_group_or_none(name)
        if not sg:
            sg = self.create_group(name, description, auth_ssh=auth_ssh,
                                   auth_group_traffic=auth_group_traffic,
                                   vpc_id=vpc_id)
        return sg

    def get_security_group(self, groupname):
        try:
            return self.get_security_groups(
                filters={'group-name': groupname})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidGroup.NotFound":
                raise exception.SecurityGroupDoesNotExist(groupname)
            raise
        except IndexError:
            raise exception.SecurityGroupDoesNotExist(groupname)

    def get_security_groups(self, filters=None):
        """
        Returns all security groups on this EC2 account
        """
        return self.conn.get_all_security_groups(filters=filters)

    def get_permission_or_none(self, group, ip_protocol, from_port, to_port,
                               cidr_ip=None):
        """
        Returns the rule with the specified port range permission (ip_protocol,
        from_port, to_port, cidr_ip) defined or None if no such rule exists
        """
        for rule in group.rules:
            if rule.ip_protocol != ip_protocol:
                continue
            if int(rule.from_port) != from_port:
                continue
            if int(rule.to_port) != to_port:
                continue
            if cidr_ip:
                cidr_grants = [g for g in rule.grants if g.cidr_ip == cidr_ip]
                if not cidr_grants:
                    continue
            return rule

    def has_permission(self, group, ip_protocol, from_port, to_port, cidr_ip):
        """
        Checks whether group has the specified port range permission
        (ip_protocol, from_port, to_port, cidr_ip) defined
        """
        for rule in group.rules:
            if rule.ip_protocol != ip_protocol:
                continue
            if int(rule.from_port) != from_port:
                continue
            if int(rule.to_port) != to_port:
                continue
            cidr_grants = [g for g in rule.grants if g.cidr_ip == cidr_ip]
            if not cidr_grants:
                continue
            return True
        return False

    def create_placement_group(self, name):
        """
        Create a new placement group for your account.
        This will create the placement group within the region you
        are currently connected to.
        """
        log.info("Creating placement group %s..." % name)
        success = self.conn.create_placement_group(name)
        if not success:
            log.debug(
                "failed to create placement group '%s' (error = %s)" %
                (name, success))
            raise exception.AWSError(
                "failed to create placement group '%s'" % name)
        pg = self.get_placement_group_or_none(name)
        while not pg:
            log.info("Waiting for placement group %s..." % name)
            time.sleep(3)
            pg = self.get_placement_group_or_none(name)
        return pg

    def get_placement_groups(self, filters=None):
        return self.conn.get_all_placement_groups(filters=filters)

    def get_placement_group(self, groupname=None):
        try:
            return self.get_placement_groups(filters={'group-name':
                                                      groupname})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidPlacementGroup.Unknown":
                raise exception.PlacementGroupDoesNotExist(groupname)
            raise
        except IndexError:
            raise exception.PlacementGroupDoesNotExist(groupname)

    def get_placement_group_or_none(self, name):
        """
        Returns placement group with name if it exists otherwise returns None
        """
        try:
            return self.get_placement_group(name)
        except exception.PlacementGroupDoesNotExist:
            pass

    def get_or_create_placement_group(self, name):
        """
        Try to return a placement group by name.
        If the group is not found, attempt to create it.
        """
        try:
            return self.get_placement_group(name)
        except exception.PlacementGroupDoesNotExist:
            pg = self.create_placement_group(name)
            return pg

    def request_instances(self, image_id, price=None, instance_type='m1.small',
                          min_count=1, max_count=1, count=1, key_name=None,
                          security_groups=None, security_group_ids=None,
                          launch_group=None,
                          availability_zone_group=None, placement=None,
                          user_data=None, placement_group=None,
                          block_device_map=None, subnet_id=None,
                          network_interfaces=None):
        """
        Convenience method for running spot or flat-rate instances
        """
        if not block_device_map:
            img = self.get_image(image_id)
            instance_store = img.root_device_type == 'instance-store'
            if instance_type == 'm1.small' and img.architecture == "i386":
                # Needed for m1.small + 32bit AMI (see gh-329)
                instance_store = True
            use_ephemeral = instance_type != 't2.micro'
            bdmap = self.create_block_device_map(
                add_ephemeral_drives=use_ephemeral,
                num_ephemeral_drives=24,
                instance_store=instance_store)
            # Prune drives from runtime block device map that may override EBS
            # volumes specified in the AMIs block device map
            for dev in img.block_device_mapping:
                bdt = img.block_device_mapping.get(dev)
                if not bdt.ephemeral_name and dev in bdmap:
                    log.debug("EBS volume already mapped to %s by AMI" % dev)
                    log.debug("Removing %s from runtime block device map" %
                              dev)
                    bdmap.pop(dev)
            if img.root_device_name in img.block_device_mapping:
                log.debug("Forcing delete_on_termination for AMI: %s" % img.id)
                root = img.block_device_mapping[img.root_device_name]
                # specifying the AMI's snapshot in the custom block device
                # mapping when you dont own the AMI causes an error on launch
                root.snapshot_id = None
                root.delete_on_termination = True
                # AWS API doesn't support any value for this flag for the root
                # device of a new instance (see: boto#2587)
                if hasattr(root, 'encrypted'):
                    root.encrypted = None
                bdmap[img.root_device_name] = root
            block_device_map = bdmap
        shared_kwargs = dict(instance_type=instance_type,
                             key_name=key_name,
                             subnet_id=subnet_id,
                             placement=placement,
                             placement_group=placement_group,
                             user_data=user_data,
                             block_device_map=block_device_map,
                             network_interfaces=network_interfaces)
        if price:
            return self.request_spot_instances(
                price, image_id,
                count=count, launch_group=launch_group,
                security_group_ids=security_group_ids,
                availability_zone_group=availability_zone_group,
                **shared_kwargs)
        else:
            return self.run_instances(
                image_id,
                min_count=min_count, max_count=max_count,
                security_groups=security_groups,
                **shared_kwargs)

    def request_spot_instances(self, price, image_id, instance_type='m1.small',
                               count=1, launch_group=None, key_name=None,
                               availability_zone_group=None,
                               security_group_ids=None, subnet_id=None,
                               placement=None, placement_group=None,
                               user_data=None, block_device_map=None,
                               network_interfaces=None):
        kwargs = locals()
        kwargs.pop('self')
        return self.conn.request_spot_instances(**kwargs)

    def _wait_for_propagation(self, obj_ids, fetch_func, id_filter, obj_name,
                              max_retries=60, interval=5):
        """
        Wait for a list of object ids to appear in the AWS API. Requires a
        function that fetches the objects and also takes a filters kwarg. The
        id_filter specifies the id filter to use for the objects and
        obj_name describes the objects for log messages.
        """
        filters = {id_filter: obj_ids}
        num_objs = len(obj_ids)
        num_reqs = 0
        reqs_ids = []
        max_retries = max(1, max_retries)
        interval = max(1, interval)
        widgets = ['', progressbar.Fraction(), ' ',
                   progressbar.Bar(marker=progressbar.RotatingMarker()), ' ',
                   progressbar.Percentage(), ' ', ' ']
        log.info("Waiting for %s to propagate..." % obj_name)
        pbar = progressbar.ProgressBar(widgets=widgets,
                                       maxval=num_objs).start()
        try:
            for i in range(max_retries + 1):
                reqs = fetch_func(filters=filters)
                reqs_ids = [req.id for req in reqs]
                num_reqs = len(reqs)
                pbar.update(num_reqs)
                if num_reqs != num_objs:
                    log.debug("%d: only %d/%d %s have "
                              "propagated - sleeping..." %
                              (i, num_reqs, num_objs, obj_name))
                    if i != max_retries:
                        time.sleep(interval)
                else:
                    return
        finally:
            if not pbar.finished:
                pbar.finish()
        missing = [oid for oid in obj_ids if oid not in reqs_ids]
        raise exception.PropagationException(
            "Failed to fetch %d/%d %s after %d seconds: %s" %
            (num_reqs, num_objs, obj_name, max_retries * interval,
             ', '.join(missing)))

    def wait_for_propagation(self, instances=None, spot_requests=None,
                             max_retries=60, interval=5):
        """
        Wait for newly created instances and/or spot_requests to register in
        the AWS API by repeatedly calling get_all_{instances, spot_requests}.
        Calling this method directly after creating new instances or spot
        requests before operating on them helps to avoid eventual consistency
        errors about instances or spot requests not existing.
        """
        if spot_requests:
            spot_ids = [getattr(s, 'id', s) for s in spot_requests]
            self._wait_for_propagation(
                spot_ids, self.get_all_spot_requests,
                'spot-instance-request-id', 'spot requests',
                max_retries=max_retries, interval=interval)
        if instances:
            instance_ids = [getattr(i, 'id', i) for i in instances]
            self._wait_for_propagation(
                instance_ids, self.get_all_instances, 'instance-id',
                'instances', max_retries=max_retries, interval=interval)

    def run_instances(self, image_id, instance_type='m1.small', min_count=1,
                      max_count=1, key_name=None, security_groups=None,
                      placement=None, user_data=None, placement_group=None,
                      block_device_map=None, subnet_id=None,
                      network_interfaces=None):
        kwargs = dict(
            instance_type=instance_type,
            min_count=min_count,
            max_count=max_count,
            key_name=key_name,
            subnet_id=subnet_id,
            placement=placement,
            user_data=user_data,
            placement_group=placement_group,
            block_device_map=block_device_map,
            network_interfaces=network_interfaces
        )
        if subnet_id:
            kwargs.update(
                security_group_ids=self.get_securityids_from_names(
                    security_groups))
            return self.conn.run_instances(image_id, **kwargs)
        else:
            kwargs.update(security_groups=security_groups)
            return self.conn.run_instances(image_id, **kwargs)

    def create_image(self, instance_id, name, description=None,
                     no_reboot=False):
        return self.conn.create_image(instance_id, name,
                                      description=description,
                                      no_reboot=no_reboot)

    def register_image(self, name, description=None, image_location=None,
                       architecture=None, kernel_id=None, ramdisk_id=None,
                       root_device_name=None, block_device_map=None,
                       virtualization_type=None, sriov_net_support=None,
                       snapshot_id=None):
        kwargs = locals()
        kwargs.pop('self')
        return self.conn.register_image(**kwargs)

    def delete_keypair(self, name):
        return self.conn.delete_key_pair(name)

    def import_keypair(self, name, rsa_key_file):
        """
        Import an existing RSA key file to EC2

        Returns boto.ec2.keypair.KeyPair
        """
        k = sshutils.get_rsa_key(rsa_key_file)
        pub_material = sshutils.get_public_key(k)
        return self.conn.import_key_pair(name, pub_material)

    def create_keypair(self, name, output_file=None):
        """
        Create a new EC2 keypair and optionally save to output_file

        Returns boto.ec2.keypair.KeyPair
        """
        if output_file:
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                raise exception.BaseException(
                    "output directory does not exist")
            if os.path.exists(output_file):
                raise exception.BaseException(
                    "cannot save keypair %s: file already exists" %
                    output_file)
        try:
            kp = self.conn.create_key_pair(name)
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidKeyPair.Duplicate":
                raise exception.KeyPairAlreadyExists(name)
            raise
        if output_file:
            try:
                kfile = open(output_file, 'wb')
                kfile.write(kp.material)
                kfile.close()
                os.chmod(output_file, 0400)
            except IOError as e:
                raise exception.BaseException(str(e))
        return kp

    def get_keypairs(self, filters={}):
        return self.conn.get_all_key_pairs(filters=filters)

    def get_keypair(self, keypair):
        try:
            return self.get_keypairs(filters={'key-name': keypair})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidKeyPair.NotFound":
                raise exception.KeyPairDoesNotExist(keypair)
            raise
        except IndexError:
            raise exception.KeyPairDoesNotExist(keypair)

    def get_keypair_or_none(self, keypair):
        try:
            return self.get_keypair(keypair)
        except exception.KeyPairDoesNotExist:
            pass

    def __print_header(self, msg):
        print msg
        print "-" * len(msg)

    def get_image_name(self, img):
        image_name = re.sub('\.manifest\.xml$', '',
                            img.location.split('/')[-1])
        return image_name

    def get_instance_user_data(self, instance_id):
        try:
            attrs = self.conn.get_instance_attribute(instance_id, 'userData')
            user_data = attrs.get('userData', '') or ''
            return base64.b64decode(user_data)
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidInstanceID.NotFound":
                raise exception.InstanceDoesNotExist(instance_id)
            raise e

    def get_securityids_from_names(self, groupnames):
        name_id = dict([(sec.name, sec.id) for sec in
                        self.get_all_security_groups(groupnames)])
        return [name_id[gname] for gname in groupnames if gname in name_id]

    def get_all_instances(self, instance_ids=[], filters={}):
        # little path to since vpc can't hadle filters with group-name
        # TODO : dev Tue Apr 24 18:25:58 2012
        # should move all code to instance.group-id
        if 'group-name' in filters:
            groupname = filters['group-name']
            try:
                secid = self.get_securityids_from_names([groupname])[0]
                filters['instance.group-id'] = secid
            except IndexError:
                return []  # Haven't created the security group in aws yet
            del filters['group-name']

        reservations = self.conn.get_all_instances(instance_ids,
                                                   filters=filters)
        instances = []
        for res in reservations:
            insts = res.instances
            instances.extend(insts)
        return instances

    def get_instance(self, instance_id):
        try:
            return self.get_all_instances(
                filters={'instance-id': instance_id})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidInstanceID.NotFound":
                raise exception.InstanceDoesNotExist(instance_id)
            raise
        except IndexError:
            raise exception.InstanceDoesNotExist(instance_id)

    def is_valid_conn(self):
        try:
            self.get_all_instances()
            return True
        except boto.exception.EC2ResponseError as e:
            cred_errs = ['AuthFailure', 'SignatureDoesNotMatch']
            if e.error_code in cred_errs:
                return False
            raise

    def get_all_spot_requests(self, spot_ids=[], filters=None):
        spots = self.conn.get_all_spot_instance_requests(spot_ids,
                                                         filters=filters)
        return spots

    def list_all_spot_instances(self, show_closed=False):
        s = self.conn.get_all_spot_instance_requests()
        if not s:
            log.info("No spot instance requests found...")
            return
        spots = []
        for spot in s:
            if spot.state in ['closed', 'cancelled'] and not show_closed:
                continue
            state = spot.state or 'N/A'
            spot_id = spot.id or 'N/A'
            spots.append(spot_id)
            type = spot.type
            instance_id = spot.instance_id or 'N/A'
            create_time = spot.create_time or 'N/A'
            launch_group = spot.launch_group or 'N/A'
            zone_group = spot.availability_zone_group or 'N/A'
            price = spot.price or 'N/A'
            status = spot.status.code or 'N/A'
            message = spot.status.message or 'N/A'
            lspec = spot.launch_specification
            instance_type = lspec.instance_type
            image_id = lspec.image_id
            zone = lspec.placement
            groups = ', '.join([g.id for g in lspec.groups])
            print "id: %s" % spot_id
            print "price: $%0.2f" % price
            print "status: %s" % status
            print "message: %s" % message
            print "spot_request_type: %s" % type
            print "state: %s" % state
            print "instance_id: %s" % instance_id
            print "instance_type: %s" % instance_type
            print "image_id: %s" % image_id
            print "zone: %s" % zone
            print "create_time: %s" % create_time
            print "launch_group: %s" % launch_group
            print "zone_group: %s" % zone_group
            print "security_groups: %s" % groups
            print
        if not spots:
            log.info("No spot instance requests found...")
        else:
            print 'Total: %s' % len(spots)

    def show_instance(self, instance):
        instance_id = instance.id or 'N/A'
        groups = ', '.join([g.name for g in instance.groups])
        dns_name = instance.dns_name or 'N/A'
        private_dns_name = instance.private_dns_name or 'N/A'
        state = instance.state or 'N/A'
        private_ip = instance.private_ip_address or 'N/A'
        public_ip = instance.ip_address or 'N/A'
        zone = instance.placement or 'N/A'
        ami = instance.image_id or 'N/A'
        virt_type = instance.virtualization_type or 'N/A'
        instance_type = instance.instance_type or 'N/A'
        keypair = instance.key_name or 'N/A'
        uptime = utils.get_elapsed_time(instance.launch_time) or 'N/A'
        tags = ', '.join(['%s=%s' % (k, v) for k, v in
                          instance.tags.iteritems()]) or 'N/A'
        vpc_id = instance.vpc_id or 'N/A'
        subnet_id = instance.subnet_id or 'N/A'
        if state == 'stopped':
            uptime = 'N/A'
        print "id: %s" % instance_id
        print "dns_name: %s" % dns_name
        print "private_dns_name: %s" % private_dns_name
        if instance.reason:
            print "state: %s (%s)" % (state, instance.reason)
        else:
            print "state: %s" % state
        print "public_ip: %s" % public_ip
        print "private_ip: %s" % private_ip
        print "vpc: %s" % vpc_id
        print "subnet: %s" % subnet_id
        print "zone: %s" % zone
        print "ami: %s" % ami
        print "virtualization: %s" % virt_type
        print "type: %s" % instance_type
        print "groups: %s" % groups
        print "keypair: %s" % keypair
        print "uptime: %s" % uptime
        print "tags: %s" % tags
        print

    def list_all_instances(self, show_terminated=False):
        tstates = ['shutting-down', 'terminated']
        insts = self.get_all_instances()
        if not show_terminated:
            insts = [i for i in insts if i.state not in tstates]
        if not insts:
            log.info("No instances found")
            return
        for instance in insts:
            self.show_instance(instance)
        print 'Total: %s' % len(insts)

    def list_images(self, images, sort_key=None, reverse=False):
        def get_key(obj):
            return ' '.join([obj.region.name, obj.location])
        if not sort_key:
            sort_key = get_key
        imgs_i386 = [img for img in images if img.architecture == "i386"]
        imgs_i386.sort(key=sort_key, reverse=reverse)
        imgs_x86_64 = [img for img in images if img.architecture == "x86_64"]
        imgs_x86_64.sort(key=sort_key, reverse=reverse)
        print
        self.__list_images("32bit Images:", imgs_i386)
        self.__list_images("\n64bit Images:", imgs_x86_64)
        print "\ntotal images: %d" % len(images)
        print

    def list_registered_images(self):
        images = self.registered_images
        log.info("Your registered images:")
        self.list_images(images)

    def list_executable_images(self):
        images = self.executable_images
        log.info("Private images owned by other users that you can execute:")
        self.list_images(images)

    def __list_images(self, msg, imgs):
        counter = 0
        self.__print_header(msg)
        for img in imgs:
            name = self.get_image_name(img)
            template = "[%d] %s %s %s"
            if img.virtualization_type == 'hvm':
                template += ' (HVM-EBS)'
            elif img.root_device_type == 'ebs':
                template += ' (EBS)'
            print template % (counter, img.id, img.region.name, name)
            counter += 1

    def remove_image_files(self, image_name, pretend=True):
        if pretend:
            log.info("Pretending to remove image files...")
        else:
            log.info('Removing image files...')
        files = self.get_image_files(image_name)
        for f in files:
            if pretend:
                log.info("Would remove file: %s" % f.name)
            else:
                log.info('Removing file %s' % f.name)
                f.delete()
        if not pretend:
            files = self.get_image_files(image_name)
            if len(files) != 0:
                log.warn('Not all files deleted, recursing...')
                self.remove_image_files(image_name, pretend)

    @print_timing("Removing image")
    def remove_image(self, image_name, pretend=True, keep_image_data=True):
        img = self.get_image(image_name)
        if pretend:
            log.info('Pretending to deregister AMI: %s' % img.id)
        else:
            log.info('Deregistering AMI: %s' % img.id)
            img.deregister()
        if img.root_device_type == "instance-store" and not keep_image_data:
            self.remove_image_files(img, pretend=pretend)
        elif img.root_device_type == "ebs" and not keep_image_data:
            rootdevtype = img.block_device_mapping.get('/dev/sda1', None)
            if rootdevtype:
                snapid = rootdevtype.snapshot_id
                if snapid:
                    snap = self.get_snapshot(snapid)
                    if pretend:
                        log.info("Would remove snapshot: %s" % snapid)
                    else:
                        log.info("Removing snapshot: %s" % snapid)
                        snap.delete()

    def list_starcluster_public_images(self):
        images = self.conn.get_all_images(owners=[static.STARCLUSTER_OWNER_ID])
        log.info("Listing all public StarCluster images...")
        imgs = [img for img in images if img.is_public]

        def sc_public_sort(obj):
            split = obj.name.split('-')
            osname, osversion, arch = split[2:5]
            osversion = float(osversion)
            rc = 0
            if split[-1].startswith('rc'):
                rc = int(split[-1].replace('rc', ''))
            return (osversion, rc)
        self.list_images(imgs, sort_key=sc_public_sort, reverse=True)

    def create_volume(self, size, zone, snapshot_id=None):
        msg = "Creating %sGB volume in zone %s" % (size, zone)
        if snapshot_id:
            msg += " from snapshot %s" % snapshot_id
        log.info(msg)
        return self.conn.create_volume(size, zone, snapshot_id)

    def remove_volume(self, volume_id):
        vol = self.get_volume(volume_id)
        vol.delete()

    def list_keypairs(self):
        keypairs = self.keypairs
        if not keypairs:
            log.info("No keypairs found...")
            return
        max_length = max([len(key.name) for key in keypairs])
        templ = "%" + str(max_length) + "s  %s"
        for key in self.keypairs:
            print templ % (key.name, key.fingerprint)

    def list_zones(self, region=None):
        conn = self.conn
        if region:
            regs = self.conn.get_all_regions()
            regions = [r.name for r in regs]
            if region not in regions:
                raise exception.RegionDoesNotExist(region)
            for reg in regs:
                if reg.name == region:
                    region = reg
                    break
            kwargs = {}
            kwargs.update(self._kwargs)
            kwargs.update(dict(region=region))
            conn = self.connection_authenticator(
                self.aws_access_key_id, self.aws_secret_access_key, **kwargs)
        for zone in conn.get_all_zones():
            print 'name: ', zone.name
            print 'region: ', zone.region.name
            print 'status: ', zone.state
            print

    def get_zones(self, filters=None):
        return self.conn.get_all_zones(filters=filters)

    def get_zone(self, zone):
        """
        Return zone object representing an EC2 availability zone
        Raises exception.ZoneDoesNotExist if not successful
        """
        try:
            return self.get_zones(filters={'zone-name': zone})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidZone.NotFound":
                raise exception.ZoneDoesNotExist(zone, self.region.name)
        except IndexError:
            raise exception.ZoneDoesNotExist(zone, self.region.name)

    def get_zone_or_none(self, zone):
        """
        Return zone object representing an EC2 availability zone
        Returns None if unsuccessful
        """
        try:
            return self.get_zone(zone)
        except exception.ZoneDoesNotExist:
            pass

    def create_s3_image(self, instance_id, key_location, aws_user_id,
                        ec2_cert, ec2_private_key, bucket, image_name="image",
                        description=None, kernel_id=None, ramdisk_id=None,
                        remove_image_files=False, **kwargs):
        """
        Create instance-store (S3) image from running instance
        """
        icreator = image.S3ImageCreator(self, instance_id, key_location,
                                        aws_user_id, ec2_cert,
                                        ec2_private_key, bucket,
                                        image_name=image_name,
                                        description=description,
                                        kernel_id=kernel_id,
                                        ramdisk_id=ramdisk_id,
                                        remove_image_files=remove_image_files)
        return icreator.create_image()

    def create_ebs_image(self, instance_id, key_location, name,
                         description=None, snapshot_description=None,
                         kernel_id=None, ramdisk_id=None, root_vol_size=15,
                         **kwargs):
        """
        Create EBS-backed image from running instance
        """
        sdescription = snapshot_description
        icreator = image.EBSImageCreator(self, instance_id, key_location,
                                         name, description=description,
                                         snapshot_description=sdescription,
                                         kernel_id=kernel_id,
                                         ramdisk_id=ramdisk_id,
                                         **kwargs)
        return icreator.create_image(size=root_vol_size)

    def get_images(self, filters=None):
        return self.conn.get_all_images(filters=filters)

    def get_image(self, image_id):
        """
        Return image object representing an AMI.
        Raises exception.AMIDoesNotExist if unsuccessful
        """
        try:
            return self.get_images(filters={'image-id': image_id})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidAMIID.NotFound":
                raise exception.AMIDoesNotExist(image_id)
            raise
        except IndexError:
            raise exception.AMIDoesNotExist(image_id)

    def get_image_or_none(self, image_id):
        """
        Return image object representing an AMI.
        Returns None if unsuccessful
        """
        try:
            return self.get_image(image_id)
        except exception.AMIDoesNotExist:
            pass

    def get_image_files(self, image):
        """
        Returns a list of files on S3 for an EC2 instance-store (S3-backed)
        image. This includes the image's manifest and part files.
        """
        if not hasattr(image, 'id'):
            image = self.get_image(image)
        if image.root_device_type == 'ebs':
            raise exception.AWSError(
                "Image %s is an EBS image. No image files on S3." % image.id)
        bucket = self.get_image_bucket(image)
        bname = re.escape(bucket.name)
        prefix = re.sub('^%s\/' % bname, '', image.location)
        prefix = re.sub('\.manifest\.xml$', '', prefix)
        files = bucket.list(prefix=prefix)
        manifest_regex = re.compile(r'%s\.manifest\.xml' % prefix)
        part_regex = re.compile(r'%s\.part\.(\d*)' % prefix)
        # boto with eucalyptus returns boto.s3.prefix.Prefix class at the
        # end of the list, we ignore these by checking for delete attr
        files = [f for f in files if hasattr(f, 'delete') and
                 part_regex.match(f.name) or manifest_regex.match(f.name)]
        return files

    def get_image_bucket(self, image):
        bucket_name = image.location.split('/')[0]
        return self.s3.get_bucket(bucket_name)

    def get_image_manifest(self, image):
        return image.location.split('/')[-1]

    @print_timing("Migrating image")
    def migrate_image(self, image_id, destbucket, migrate_manifest=False,
                      kernel_id=None, ramdisk_id=None, region=None, cert=None,
                      private_key=None):
        """
        Migrate image_id files to destbucket
        """
        if migrate_manifest:
            utils.check_required(['ec2-migrate-manifest'])
            if not cert:
                raise exception.BaseException("no cert specified")
            if not private_key:
                raise exception.BaseException("no private_key specified")
            if not kernel_id:
                raise exception.BaseException("no kernel_id specified")
            if not ramdisk_id:
                raise exception.BaseException("no ramdisk_id specified")
        image = self.get_image(image_id)
        if image.root_device_type == "ebs":
            raise exception.AWSError(
                "The image you wish to migrate is EBS-based. " +
                "This method only works for instance-store images")
        files = self.get_image_files(image)
        if not files:
            log.info("No files found for image: %s" % image_id)
            return
        log.info("Migrating image: %s" % image_id)
        widgets = [files[0].name, progressbar.Percentage(), ' ',
                   progressbar.Bar(marker=progressbar.RotatingMarker()), ' ',
                   progressbar.ETA(), ' ', ' ']
        counter = 0
        num_files = len(files)
        pbar = progressbar.ProgressBar(widgets=widgets,
                                       maxval=num_files).start()
        for f in files:
            widgets[0] = "%s: (%s/%s)" % (f.name, counter + 1, num_files)
            # copy file to destination bucket with the same name
            f.copy(destbucket, f.name)
            pbar.update(counter)
            counter += 1
        pbar.finish()
        if migrate_manifest:
            dbucket = self.s3.get_bucket(destbucket)
            manifest_key = dbucket.get_key(self.get_image_manifest(image))
            f = tempfile.NamedTemporaryFile()
            manifest_key.get_contents_to_file(f.file)
            f.file.close()
            cmd = ('ec2-migrate-manifest -c %s -k %s -m %s --kernel %s ' +
                   '--ramdisk %s --no-mapping ') % (cert, private_key,
                                                    f.name, kernel_id,
                                                    ramdisk_id)
            register_cmd = "ec2-register %s/%s" % (destbucket,
                                                   manifest_key.name)
            if region:
                cmd += '--region %s' % region
                register_cmd += " --region %s" % region
            log.info("Migrating manifest file...")
            retval = os.system(cmd)
            if retval != 0:
                raise exception.BaseException(
                    "ec2-migrate-manifest failed with status %s" % retval)
            f.file = open(f.name, 'r')
            manifest_key.set_contents_from_file(f.file)
            # needed so that EC2 has permission to READ the manifest file
            manifest_key.add_email_grant('READ', 'za-team@amazon.com')
            f.close()
            os.unlink(f.name + '.bak')
            log.info("Manifest migrated successfully. You can now run:\n" +
                     register_cmd + "\nto register your migrated image.")

    def copy_image(self, source_region, source_image_id, name=None,
                   description=None, client_token=None, wait_for_copy=False):
        kwargs = locals()
        kwargs.pop('self')
        kwargs.pop('wait_for_copy')
        log.info("Copying %s from %s to %s" % (source_image_id, source_region,
                                               self.region.name))
        resp = self.conn.copy_image(**kwargs)
        log.info("New AMI in region %s: %s" %
                 (self.region.name, resp.image_id))
        if wait_for_copy:
            img = self.get_image(resp.image_id)
            self.wait_for_ami(img)
        return resp

    def wait_for_ami(self, ami):
        if ami.root_device_type == 'ebs':
            root = ami.block_device_mapping.get(ami.root_device_name)
            if root.snapshot_id:
                self.wait_for_snapshot(self.get_snapshot(root.snapshot_id))
            else:
                log.warn("The root device snapshot id is not yet available")
        s = utils.get_spinner("Waiting for '%s' to become available" % ami.id)
        try:
            while ami.state != 'available':
                ami.update()
                time.sleep(10)
        finally:
            s.stop()

    def copy_image_to_all_regions(self, source_region, source_image_id,
                                  name=None, description=None,
                                  client_token=None, add_region_to_desc=False,
                                  wait_for_copies=False):
        current_region = self.region
        self.connect_to_region(source_region)
        src_img = self.get_image(source_image_id)
        regions = self.regions.copy()
        regions.pop(source_region)
        log.info("Copying %s to regions:\n%s" %
                 (src_img.id, ', '.join(regions.keys())))
        name = name or src_img.name
        resps = {}
        for r in regions:
            self.connect_to_region(r)
            desc = description or ''
            if add_region_to_desc:
                desc += ' (%s)' % r.upper()
            resp = self.copy_image(src_img.region.name, src_img.id, name=name,
                                   description=desc,
                                   client_token=client_token)
            resps[r] = resp
        if wait_for_copies:
            for r in resps:
                self.connect_to_region(r)
                img = self.get_image(resps[r].image_id)
                self.wait_for_ami(img)
        self.connect_to_region(current_region.name)
        return resps

    def create_block_device_map(self, root_snapshot_id=None,
                                root_device_name='/dev/sda1',
                                add_ephemeral_drives=False,
                                num_ephemeral_drives=24, instance_store=False):
        """
        Utility method for building a new block_device_map for a given snapshot
        id. This is useful when creating a new image from a volume snapshot.
        The returned block device map can be used with self.register_image
        """
        bmap = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        if root_snapshot_id:
            sda1 = boto.ec2.blockdevicemapping.BlockDeviceType()
            sda1.snapshot_id = root_snapshot_id
            sda1.delete_on_termination = True
            bmap[root_device_name] = sda1
        if add_ephemeral_drives:
            if not instance_store:
                drives = ['/dev/xvd%s%%s' % s for s in string.lowercase]
                for i in range(num_ephemeral_drives):
                    j, k = i % 26, i / 26
                    device_fmt = drives[k]
                    eph = boto.ec2.blockdevicemapping.BlockDeviceType()
                    eph.ephemeral_name = 'ephemeral%d' % i
                    bmap[device_fmt % chr(ord('a') + j)] = eph
            else:
                drives = ['sd%s%d' % (s, i) for i in range(1, 10)
                          for s in string.lowercase[1:]]
                for i in range(num_ephemeral_drives):
                    eph = boto.ec2.blockdevicemapping.BlockDeviceType()
                    eph.ephemeral_name = 'ephemeral%d' % i
                    bmap[drives[i]] = eph
        return bmap

    @print_timing("Downloading image")
    def download_image_files(self, image_id, destdir):
        """
        Downloads the manifest.xml and all AMI parts for image_id to destdir
        """
        if not os.path.isdir(destdir):
            raise exception.BaseException(
                "destination directory '%s' does not exist" % destdir)
        widgets = ['file: ', progressbar.Percentage(), ' ',
                   progressbar.Bar(marker=progressbar.RotatingMarker()), ' ',
                   progressbar.ETA(), ' ', progressbar.FileTransferSpeed()]
        files = self.get_image_files(image_id)

        def _dl_progress_cb(trans, total):
            pbar.update(trans)
        log.info("Downloading image: %s" % image_id)
        for file in files:
            widgets[0] = "%s:" % file.name
            pbar = progressbar.ProgressBar(widgets=widgets,
                                           maxval=file.size).start()
            file.get_contents_to_filename(os.path.join(destdir, file.name),
                                          cb=_dl_progress_cb)
            pbar.finish()

    def list_image_files(self, image_id):
        """
        Print a list of files for image_id to the screen
        """
        files = self.get_image_files(image_id)
        for file in files:
            print file.name

    @property
    def instances(self):
        return self.get_all_instances()

    @property
    def keypairs(self):
        return self.get_keypairs()

    def terminate_instances(self, instances=None):
        if instances:
            self.conn.terminate_instances(instances)

    def get_volumes(self, filters=None):
        """
        Returns a list of all EBS volumes
        """
        return self.conn.get_all_volumes(filters=filters)

    def get_volume(self, volume_id):
        """
        Returns EBS volume object representing volume_id.
        Raises exception.VolumeDoesNotExist if unsuccessful
        """
        try:
            return self.get_volumes(filters={'volume-id': volume_id})[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidVolume.NotFound":
                raise exception.VolumeDoesNotExist(volume_id)
            raise
        except IndexError:
            raise exception.VolumeDoesNotExist(volume_id)

    def get_volume_or_none(self, volume_id):
        """
        Returns EBS volume object representing volume_id.
        Returns None if unsuccessful
        """
        try:
            return self.get_volume(volume_id)
        except exception.VolumeDoesNotExist:
            pass

    def wait_for_volume(self, volume, status=None, state=None,
                        refresh_interval=5, log_func=log.info):
        if status:
            log_func("Waiting for %s to become '%s'..." % (volume.id, status),
                     extra=dict(__nonewline__=True))
            s = spinner.Spinner()
            s.start()
            while volume.update() != status:
                time.sleep(refresh_interval)
            s.stop()
        if state:
            log_func("Waiting for %s to transition to: %s... " %
                     (volume.id, state), extra=dict(__nonewline__=True))
            if not status:
                volume.update()
            s = spinner.Spinner()
            s.start()
            while volume.attachment_state() != state:
                time.sleep(refresh_interval)
                volume.update()
            s.stop()

    def wait_for_snapshot(self, snapshot, refresh_interval=30):
        snap = snapshot
        log.info("Waiting for snapshot to complete: %s" % snap.id)
        widgets = ['%s: ' % snap.id, '',
                   progressbar.Bar(marker=progressbar.RotatingMarker()),
                   '', progressbar.Percentage(), ' ', progressbar.ETA()]
        pbar = progressbar.ProgressBar(widgets=widgets, maxval=100).start()
        while snap.status != 'completed':
            try:
                progress = int(snap.update().replace('%', ''))
                if not pbar.finished:
                    pbar.update(progress)
            except ValueError:
                time.sleep(5)
                continue
            if snap.status != 'completed':
                time.sleep(refresh_interval)
        if not pbar.finished:
            pbar.finish()

    def create_snapshot(self, vol, description=None, wait_for_snapshot=False,
                        refresh_interval=30):
        log.info("Creating snapshot of volume: %s" % vol.id)
        snap = vol.create_snapshot(description)
        if wait_for_snapshot:
            self.wait_for_snapshot(snap, refresh_interval)
        return snap

    def get_snapshots(self, volume_ids=[], filters=None, owner='self'):
        """
        Returns a list of all EBS volume snapshots
        """
        filters = filters or {}
        if volume_ids:
            filters['volume-id'] = volume_ids
        return self.conn.get_all_snapshots(owner=owner, filters=filters)

    def get_snapshot(self, snapshot_id, owner='self'):
        """
        Returns EBS snapshot object for snapshot_id.

        Raises exception.SnapshotDoesNotExist if unsuccessful
        """
        try:
            return self.get_snapshots(filters={'snapshot-id': snapshot_id},
                                      owner=owner)[0]
        except boto.exception.EC2ResponseError as e:
            if e.error_code == "InvalidSnapshot.NotFound":
                raise exception.SnapshotDoesNotExist(snapshot_id)
            raise
        except IndexError:
            raise exception.SnapshotDoesNotExist(snapshot_id)

    def list_volumes(self, volume_id=None, status=None, attach_status=None,
                     size=None, zone=None, snapshot_id=None,
                     show_deleted=False, tags=None, name=None):
        """
        Print a list of volumes to the screen
        """
        filters = {}
        if status:
            filters['status'] = status
        else:
            filters['status'] = ['creating', 'available', 'in-use', 'error']
            if show_deleted:
                filters['status'] += ['deleting', 'deleted']
        if attach_status:
            filters['attachment.status'] = attach_status
        if volume_id:
            filters['volume-id'] = volume_id
        if size:
            filters['size'] = size
        if zone:
            filters['availability-zone'] = zone
        if snapshot_id:
            filters['snapshot-id'] = snapshot_id
        if tags:
            tagkeys = []
            for tag in tags:
                val = tags.get(tag)
                if val:
                    filters["tag:%s" % tag] = val
                elif tag:
                    tagkeys.append(tag)
            if tagkeys:
                filters['tag-key'] = tagkeys
        if name:
            filters['tag:Name'] = name
        vols = self.get_volumes(filters=filters)
        vols.sort(key=lambda x: x.create_time)
        if vols:
            for vol in vols:
                print "volume_id: %s" % vol.id
                print "size: %sGB" % vol.size
                print "status: %s" % vol.status
                if vol.attachment_state():
                    print "attachment_status: %s" % vol.attachment_state()
                print "availability_zone: %s" % vol.zone
                if vol.snapshot_id:
                    print "snapshot_id: %s" % vol.snapshot_id
                snapshots = self.get_snapshots(volume_ids=[vol.id])
                if snapshots:
                    snap_list = ' '.join([snap.id for snap in snapshots])
                    print 'snapshots: %s' % snap_list
                if vol.create_time:
                    lt = utils.iso_to_localtime_tuple(vol.create_time)
                print "create_time: %s" % lt
                tags = []
                for tag in vol.tags:
                    val = vol.tags.get(tag)
                    if val:
                        tags.append("%s=%s" % (tag, val))
                    else:
                        tags.append(tag)
                if tags:
                    print "tags: %s" % ', '.join(tags)
                print
        print 'Total: %s' % len(vols)

    def get_spot_history(self, instance_type, start=None, end=None, zone=None,
                         plot=False, plot_server_interface="localhost",
                         plot_launch_browser=True, plot_web_browser=None,
                         plot_shutdown_server=True, classic=False, vpc=False):
        if start and not utils.is_iso_time(start):
            raise exception.InvalidIsoDate(start)
        if end and not utils.is_iso_time(end):
            raise exception.InvalidIsoDate(end)
        if classic and vpc:
            raise exception.BaseException(
                "classic and vpc kwargs are mutually exclusive")
        if not classic and not vpc:
            vpc = self.default_vpc is not None
            classic = not vpc
        if classic:
            pdesc = "Linux/UNIX"
            short_pdesc = "EC2-Classic"
        else:
            pdesc = "Linux/UNIX (Amazon VPC)"
            short_pdesc = "VPC"
        log.info("Fetching spot history for %s (%s)" %
                 (instance_type, short_pdesc))
        hist = self.conn.get_spot_price_history(start_time=start, end_time=end,
                                                availability_zone=zone,
                                                instance_type=instance_type,
                                                product_description=pdesc)
        if not hist:
            raise exception.SpotHistoryError(start, end)
        dates = []
        prices = []
        data = []
        for item in hist:
            timestamp = utils.iso_to_javascript_timestamp(item.timestamp)
            price = item.price
            dates.append(timestamp)
            prices.append(price)
            data.append([timestamp, price])
        maximum = max(prices)
        avg = sum(prices) / float(len(prices))
        log.info("Current price: $%.4f" % prices[0])
        log.info("Max price: $%.4f" % maximum)
        log.info("Average price: $%.4f" % avg)
        if plot:
            xaxisrange = dates[-1] - dates[0]
            xpanrange = [dates[0] - xaxisrange / 2.,
                         dates[-1] + xaxisrange / 2.]
            xzoomrange = [0.1, xpanrange[-1] - xpanrange[0]]
            minimum = min(prices)
            yaxisrange = maximum - minimum
            ypanrange = [minimum - yaxisrange / 2., maximum + yaxisrange / 2.]
            yzoomrange = [0.1, ypanrange[-1] - ypanrange[0]]
            context = dict(instance_type=instance_type,
                           start=hist[-1].timestamp, end=hist[0].timestamp,
                           time_series_data=str(data).replace('L', ''),
                           shutdown=plot_shutdown_server,
                           xpanrange=xpanrange, ypanrange=ypanrange,
                           xzoomrange=xzoomrange, yzoomrange=yzoomrange)
            log.info("", extra=dict(__raw__=True))
            log.info("Starting StarCluster Webserver...")
            s = webtools.get_template_server('web', context=context,
                                             interface=plot_server_interface)
            base_url = "http://%s:%s" % s.server_address
            shutdown_url = '/'.join([base_url, 'shutdown'])
            spot_url = "http://%s:%s/spothistory.html" % s.server_address
            log.info("Server address is %s" % base_url)
            log.info("(use CTRL-C or navigate to %s to shutdown server)" %
                     shutdown_url)
            if plot_launch_browser:
                webtools.open_browser(spot_url, plot_web_browser)
            else:
                log.info("Browse to %s to view the spot history plot" %
                         spot_url)
            s.serve_forever()
        return data

    def show_console_output(self, instance_id):
        instance = self.get_instance(instance_id)
        console_output = instance.get_console_output().output or ''
        console_output = ''.join([c for c in console_output if c in
                                  string.printable])
        if console_output:
            print console_output
        else:
            log.info("No console output available...")


class EasyS3(EasyAWS):
    DefaultHost = 's3.amazonaws.com'
    _calling_format = boto.s3.connection.OrdinaryCallingFormat()

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 aws_s3_path='/', aws_port=None, aws_is_secure=True,
                 aws_s3_host=DefaultHost, aws_proxy=None, aws_proxy_port=None,
                 aws_proxy_user=None, aws_proxy_pass=None,
                 aws_validate_certs=True, **kwargs):
        kwargs = dict(is_secure=aws_is_secure, host=aws_s3_host or
                      self.DefaultHost, port=aws_port, path=aws_s3_path,
                      proxy=aws_proxy, proxy_port=aws_proxy_port,
                      proxy_user=aws_proxy_user, proxy_pass=aws_proxy_pass,
                      validate_certs=aws_validate_certs)
        if aws_s3_host:
            kwargs.update(dict(calling_format=self._calling_format))
        super(EasyS3, self).__init__(aws_access_key_id, aws_secret_access_key,
                                     boto.connect_s3, **kwargs)

    def __repr__(self):
        return '<EasyS3: %s>' % self.conn.server_name()

    def create_bucket(self, bucket_name):
        """
        Create a new bucket on S3. bucket_name must be unique, the bucket
        namespace is shared by all AWS users
        """
        bucket_name = bucket_name.split('/')[0]
        try:
            return self.conn.create_bucket(bucket_name)
        except boto.exception.S3CreateError as e:
            if e.error_code == "BucketAlreadyExists":
                raise exception.BucketAlreadyExists(bucket_name)
            raise

    def bucket_exists(self, bucket_name):
        """
        Check if bucket_name exists on S3
        """
        try:
            return self.get_bucket(bucket_name) is not None
        except exception.BucketDoesNotExist:
            return False

    def get_or_create_bucket(self, bucket_name):
        try:
            return self.get_bucket(bucket_name)
        except exception.BucketDoesNotExist:
            log.info("Creating bucket '%s'" % bucket_name)
            return self.create_bucket(bucket_name)

    def get_bucket_or_none(self, bucket_name):
        """
        Returns bucket object representing S3 bucket
        Returns None if unsuccessful
        """
        try:
            return self.get_bucket(bucket_name)
        except exception.BucketDoesNotExist:
            pass

    def get_bucket(self, bucketname):
        """
        Returns bucket object representing S3 bucket
        """
        try:
            return self.conn.get_bucket(bucketname)
        except boto.exception.S3ResponseError as e:
            if e.error_code == "NoSuchBucket":
                raise exception.BucketDoesNotExist(bucketname)
            raise

    def list_bucket(self, bucketname):
        bucket = self.get_bucket(bucketname)
        for file in bucket.list():
            if file.name:
                print file.name

    def get_buckets(self):
        try:
            buckets = self.conn.get_all_buckets()
        except TypeError:
            # hack until boto (or eucalyptus) fixes get_all_buckets
            raise exception.AWSError("AWS credentials are not valid")
        return buckets

    def list_buckets(self):
        for bucket in self.get_buckets():
            print bucket.name

    def get_bucket_files(self, bucketname):
        bucket = self.get_bucket(bucketname)
        files = [file for file in bucket.list()]
        return files


if __name__ == "__main__":
    from starcluster.config import get_easy_ec2
    ec2 = get_easy_ec2()
    ec2.list_all_instances()
    ec2.list_registered_images()
