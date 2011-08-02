#!/usr/bin/env python
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

from starcluster import image
from starcluster import utils
from starcluster import static
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
            self._conn = self.connection_authenticator(
                self.aws_access_key_id, self.aws_secret_access_key,
                **self._kwargs)
        return self._conn


class EasyEC2(EasyAWS):
    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 aws_ec2_path='/', aws_s3_host=None, aws_s3_path='/',
                 aws_port=None, aws_region_name=None, aws_is_secure=True,
                 aws_region_host=None, cache=False, **kwargs):
        aws_region = None
        if aws_region_name and aws_region_host:
            aws_region = boto.ec2.regioninfo.RegionInfo(
                name=aws_region_name, endpoint=aws_region_host)
        kwargs = dict(is_secure=aws_is_secure, region=aws_region,
                      port=aws_port, path=aws_ec2_path)
        super(EasyEC2, self).__init__(aws_access_key_id, aws_secret_access_key,
                                      boto.connect_ec2, **kwargs)
        kwargs = dict(aws_s3_host=aws_s3_host,
                      aws_s3_path=aws_s3_path,
                      aws_port=aws_port,
                      aws_is_secure=aws_is_secure,
                      cache=cache)
        self.s3 = EasyS3(aws_access_key_id, aws_secret_access_key, **kwargs)
        self.cache = cache
        self._instance_response = None
        self._keypair_response = None
        self._images = None
        self._executable_images = None
        self._security_group_response = None
        self._regions = None

    def __repr__(self):
        return '<EasyEC2: %s (%s)>' % (self.region.name, self.region.endpoint)

    def __check_for_auth_failure(self, e):
        if e.error_code in ["AuthFailure", "SignatureDoesNotMatch"]:
            raise e

    def connect_to_region(self, region_name):
        """
        Connects to a given region if it exists, raises RegionDoesNotExist
        otherwise. Once connected, this object will return only data from the
        given region.
        """
        region = self.get_region(region_name)
        self._kwargs['region'] = region
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
        if not region_name in self.regions:
            raise exception.RegionDoesNotExist(region_name)
        return self.regions.get(region_name)

    def list_regions(self):
        """
        Print name/endpoint for all AWS regions
        """
        for r in self.regions:
            region = self.regions.get(r)
            print 'name: ', region.name
            print 'endpoint: ', region.endpoint
            print

    @property
    def registered_images(self):
        if not self.cache or self._images is None:
            self._images = self.conn.get_all_images(owners=["self"])
        return self._images

    @property
    def executable_images(self):
        if not self.cache or self._images is None:
            self._executable_images = self.conn.get_all_images(
                executable_by=["self"])
        return self._executable_images

    def get_registered_image(self, image_id):
        if not image_id.startswith('ami') or len(image_id) != 12:
            raise TypeError("invalid AMI name/id requested: %s" % image_id)
        for img in self.registered_images:
            if img.id == image_id:
                return img

    def create_group(self, name, description, auth_ssh=False,
                     auth_group_traffic=False):
        """
        Create security group with name/description. auth_ssh=True
        will open port 22 to world (0.0.0.0/0). auth_group_traffic
        will allow all traffic between instances in the same security
        group
        """
        if not name:
            return None
        log.info("Creating security group %s..." % name)
        sg = self.conn.create_security_group(name, description)
        if auth_ssh:
            sg.authorize('tcp', 22, 22, '0.0.0.0/0')
        if auth_group_traffic:
            sg.authorize('icmp', -1, -1,
                         src_group=self.get_group_or_none(name))
            sg.authorize('tcp', 1, 65535,
                         src_group=self.get_group_or_none(name))
            sg.authorize('udp', 1, 65535,
                         src_group=self.get_group_or_none(name))
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
                            auth_group_traffic=False):
        """
        Try to return a security group by name. If the group is not found,
        attempt to create it.  Description only applies to creation.

        auth_ssh - authorize ssh traffic from world
        auth_group_traffic - authorizes all traffic between members of the
                             group
        """
        sg = self.get_group_or_none(name)
        if not sg:
            sg = self.create_group(name, description, auth_ssh,
                                   auth_group_traffic)
        return sg

    def get_security_group(self, groupname):
        try:
            return self.get_security_groups(
                filters={'group-name': groupname})[0]
        except boto.exception.EC2ResponseError, e:
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

    def get_placement_group_or_none(self, name):
        """
        Returns placement group with name if it exists otherwise returns None
        """
        try:
            pg = self.conn.get_all_placement_groups(groupnames=[name])[0]
            return pg
        except boto.exception.EC2ResponseError, e:
            self.__check_for_auth_failure(e)
        except IndexError:
            pass

    def create_placement_group(self, name):
        """
        Create a new placement group for your account.
        This will create the placement group within the region you
        are currently connected to.
        """
        if not name:
            return
        log.info("Creating placement group %s..." % name)
        success = self.conn.create_placement_group(name)
        if success:
            return self.get_placement_group_or_none(name)

    def get_or_create_placement_group(self, name):
        """
        Try to return a placement group by name.
        If the group is not found, attempt to create it.
        """
        pg = self.get_placement_group_or_none(name)
        if not pg:
            pg = self.create_placement_group(name)
        return pg

    def request_instances(self, image_id, price=None, instance_type='m1.small',
                          min_count=1, max_count=1, count=1, key_name=None,
                          security_groups=None, launch_group=None,
                          availability_zone_group=None, placement=None,
                          user_data=None, placement_group=None):
        """
        Convenience method for running spot or flat-rate instances
        """
        if price:
            return self.request_spot_instances(
                price, image_id, instance_type=instance_type,
                count=count, launch_group=launch_group, key_name=key_name,
                security_groups=security_groups,
                availability_zone_group=availability_zone_group,
                placement=placement, user_data=user_data)
        else:
            return self.run_instances(
                image_id, instance_type=instance_type,
                min_count=min_count, max_count=max_count,
                key_name=key_name, security_groups=security_groups,
                placement=placement, user_data=user_data,
                placement_group=placement_group)

    def request_spot_instances(self, price, image_id, instance_type='m1.small',
                               count=1, launch_group=None, key_name=None,
                               availability_zone_group=None,
                               security_groups=None,
                               placement=None, user_data=None):
        return self.conn.request_spot_instances(
            price, image_id, instance_type=instance_type, count=count,
            launch_group=launch_group, key_name=key_name,
            security_groups=security_groups,
            availability_zone_group=availability_zone_group,
            placement=placement, user_data=user_data)

    def run_instances(self, image_id, instance_type='m1.small', min_count=1,
                      max_count=1, key_name=None, security_groups=None,
                      placement=None, user_data=None, placement_group=None):
        return self.conn.run_instances(image_id, instance_type=instance_type,
                                       min_count=min_count,
                                       max_count=max_count,
                                       key_name=key_name,
                                       security_groups=security_groups,
                                       placement=placement,
                                       user_data=user_data,
                                       placement_group=placement_group)

    def create_image(self, instance_id, name, description=None,
                     no_reboot=False):
        return self.conn.create_image(instance_id, name,
                                      description=description,
                                      no_reboot=no_reboot)

    def register_image(self, name, description=None, image_location=None,
                       architecture=None, kernel_id=None, ramdisk_id=None,
                       root_device_name=None, block_device_map=None):
        return self.conn.register_image(name=name, description=description,
                                        image_location=image_location,
                                        architecture=architecture,
                                        kernel_id=kernel_id,
                                        ramdisk_id=ramdisk_id,
                                        root_device_name=root_device_name,
                                        block_device_map=block_device_map)

    def delete_keypair(self, name):
        return self.conn.delete_key_pair(name)

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
                    "cannot save keypair %s: file already exists" % \
                    output_file)
        kp = self.conn.create_key_pair(name)
        if output_file:
            try:
                kfile = open(output_file, 'wb')
                kfile.write(kp.material)
                kfile.close()
                os.chmod(output_file, 0400)
            except IOError, e:
                raise exception.BaseException(str(e))
        return kp

    def get_keypairs(self, filters={}):
        return self.conn.get_all_key_pairs(filters=filters)

    def get_keypair(self, keypair):
        try:
            return self.get_keypairs(filters={'key-name': keypair})[0]
        except boto.exception.EC2ResponseError, e:
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
            user_data = attrs.get('userData', '')
            return base64.b64decode(user_data)
        except boto.exception.EC2ResponseError, e:
            if e.error_code == "InvalidInstanceID.NotFound":
                raise exception.InstanceDoesNotExist(instance_id)
            raise e

    def get_instance(self, instance_id):
        try:
            res = self.conn.get_all_instances(
                filters={'instance-id': instance_id})
            i = res[0].instances[0]
            # set group info
            i.groups = res[0].groups
            return i
        except boto.exception.EC2ResponseError, e:
            self.__check_for_auth_failure(e)
            raise exception.InstanceDoesNotExist(instance_id)
        except IndexError:
            # for eucalyptus, invalid instance_id returns []
            raise exception.InstanceDoesNotExist(instance_id)

    def is_valid_conn(self):
        try:
            self.get_all_instances()
            return True
        except boto.exception.EC2ResponseError, e:
            if e.status in [401, 403]:
                return False
            raise

    def get_all_spot_requests(self, spot_ids=[], filters=None):
        spots = self.conn.get_all_spot_instance_requests(spot_ids,
                                                         filters=filters)
        return spots

    def get_all_instances(self, instance_ids=[], filters=None):
        reservations = self.conn.get_all_instances(instance_ids,
                                                   filters=filters)
        instances = []
        for res in reservations:
            insts = res.instances
            for i in insts:
                # set group info
                i.groups = res.groups
            instances.extend(insts)
        return instances

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
            lspec = spot.launch_specification
            instance_type = lspec.instance_type
            image_id = lspec.image_id
            zone = lspec.placement
            groups = ', '.join([g.id for g in lspec.groups])
            print "id: %s" % spot_id
            print "price: $%0.2f" % price
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

    def list_all_instances(self, show_terminated=False):
        reservations = self.conn.get_all_instances()
        if not reservations:
            log.info("No instances found")
            return
        instances = []
        for res in reservations:
            groups = ', '.join([g.id for g in res.groups]) or 'N/A'
            for instance in res.instances:
                if instance.state in ['shutting-down', 'terminated'] \
                   and not show_terminated:
                    continue
                id = instance.id or 'N/A'
                instances.append(id)
                dns_name = instance.dns_name or 'N/A'
                private_dns_name = instance.private_dns_name or 'N/A'
                state = instance.state or 'N/A'
                private_ip = instance.private_ip_address or 'N/A'
                public_ip = instance.ip_address or 'N/A'
                zone = instance.placement or 'N/A'
                ami = instance.image_id or 'N/A'
                instance_type = instance.instance_type or 'N/A'
                keypair = instance.key_name or 'N/A'
                uptime = utils.get_elapsed_time(instance.launch_time) or 'N/A'
                print "id: %s" % id
                print "dns_name: %s" % dns_name
                print "private_dns_name: %s" % private_dns_name
                print "state: %s" % state
                print "public_ip: %s" % public_ip
                print "private_ip: %s" % private_ip
                print "zone: %s" % zone
                print "ami: %s" % ami
                print "type: %s" % instance_type
                print "groups: %s" % groups
                print "keypair: %s" % keypair
                print "uptime: %s" % uptime
                print
        if not instances:
            log.info("No instances found")

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
        files = self.get_image_files(image_name)
        for file in files:
            if pretend:
                print file
            else:
                print 'removing file %s' % file
                file.delete()

        # recursive double check
        files = self.get_image_files(image_name)
        if len(files) != 0:
            if pretend:
                log.info('Not all files deleted, would recurse...exiting')
                return
            else:
                log.info('Not all files deleted, recursing...')
                self.remove_image_files(image_name, pretend)

    @print_timing("Removing image")
    def remove_image(self, image_name, pretend=True):
        img = self.get_image(image_name)
        if pretend:
            log.info("Pretending to remove AMI: %s" % image_name)
        else:
            log.info("Removing AMI: %s" % image_name)

        # first remove image files
        log.info('Removing image files...')
        self.remove_image_files(image_name, pretend=pretend)

        # then deregister ami
        if pretend:
            log.info('Would run deregister_image for ami: %s)' % img.id)
        else:
            log.info('Deregistering ami: %s' % img.id)
            img.deregister()

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
        return self.conn.create_volume(size, zone, snapshot_id)

    def remove_volume(self, volume_id):
        vol = self.get_volume(volume_id)
        vol.delete()

    def list_keypairs(self):
        max_length = max([len(key.name) for key in self.keypairs])
        templ = "%" + str(max_length) + "s  %s"
        for key in self.keypairs:
            print templ % (key.name, key.fingerprint)

    def list_zones(self, region=None):
        conn = self.conn
        if region:
            regs = self.conn.get_all_regions()
            regions = [r.name for r in regs]
            if not region in regions:
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

    def get_zone(self, zone):
        """
        Return zone object respresenting an EC2 availability zone
        Raises exception.ZoneDoesNotExist if not successful
        """
        try:
            return self.conn.get_all_zones(zones=[zone])[0]
        except boto.exception.EC2ResponseError, e:
            self.__check_for_auth_failure(e)
            raise exception.ZoneDoesNotExist(zone, self.region.name)
        except IndexError:
            raise exception.ZoneDoesNotExist(zone, self.region.name)

    def get_zone_or_none(self, zone):
        """
        Return zone object respresenting an EC2 availability zone
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

    def get_image(self, image_id):
        """
        Return image object representing an AMI.
        Raises exception.AMIDoesNotExist if unsuccessful
        """
        try:
            return self.conn.get_all_images(image_ids=[image_id])[0]
        except boto.exception.EC2ResponseError, e:
            self.__check_for_auth_failure(e)
            raise exception.AMIDoesNotExist(image_id)
        except IndexError:
            raise exception.AMIDoesNotExist(image_id)

    def get_image_or_none(self, image_id):
        """
        Return image object representing an AMI.
        Returns None if unsuccessful
        """
        try:
            return self.get_image(image_id)
        except:
            pass

    def _get_image_files(self, image, bucket):
        """
        """
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

    def get_image_files(self, image_id):
        """
        Return list of files on S3 for image_id
        The list includes the image's manifest and part files
        """
        image = self.get_image(image_id)
        if image.root_device_type == 'ebs':
            raise exception.AWSError(
                "Image %s is an EBS image. No image files on S3." % image_id)
        bucket = self.get_image_bucket(image)
        return self._get_image_files(image, bucket)

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
        ibucket = self.get_image_bucket(image)
        files = self._get_image_files(image, ibucket)
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

    def create_root_block_device_map(self, snapshot_id,
                                     root_device_name='/dev/sda1',
                                     add_ephemeral_drives=False,
                                     ephemeral_drive_0='/dev/sdb1',
                                     ephemeral_drive_1='/dev/sdc1',
                                     ephemeral_drive_2='/dev/sdd1',
                                     ephemeral_drive_3='/dev/sde1'):
        """
        Utility method for building a new block_device_map for a given snapshot
        id. This is useful when creating a new image from a volume snapshot.
        The returned block device map can be used with self.register_image
        """
        bmap = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        sda1 = boto.ec2.blockdevicemapping.BlockDeviceType()
        sda1.snapshot_id = snapshot_id
        sda1.delete_on_termination = True
        bmap[root_device_name] = sda1
        if add_ephemeral_drives:
            sdb1 = boto.ec2.blockdevicemapping.BlockDeviceType()
            sdb1.ephemeral_name = 'ephemeral0'
            bmap[ephemeral_drive_0] = sdb1
            sdc1 = boto.ec2.blockdevicemapping.BlockDeviceType()
            sdc1.ephemeral_name = 'ephemeral1'
            bmap[ephemeral_drive_1] = sdc1
            sdd1 = boto.ec2.blockdevicemapping.BlockDeviceType()
            sdd1.ephemeral_name = 'ephemeral2'
            bmap[ephemeral_drive_2] = sdd1
            sde1 = boto.ec2.blockdevicemapping.BlockDeviceType()
            sde1.ephemeral_name = 'ephemeral3'
            bmap[ephemeral_drive_3] = sde1
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
        if not self.cache or self._instance_response is None:
            log.debug('instance_response = %s, cache = %s' %
            (self._instance_response, self.cache))
            self._instance_response = self.conn.get_all_instances()
        return self._instance_response

    @property
    def keypairs(self):
        if not self.cache or self._keypair_response is None:
            log.debug('keypair_response = %s, cache = %s' %
            (self._keypair_response, self.cache))
            self._keypair_response = self.conn.get_all_key_pairs()
        return self._keypair_response

    def terminate_instances(self, instances=None):
        if instances:
            self.conn.terminate_instances(instances)

    def get_volumes(self, filters=None):
        """
        Returns a list of all EBS volumes
        """
        try:
            return self.conn.get_all_volumes(filters=filters)
        except boto.exception.EC2ResponseError, e:
            self.__check_for_auth_failure(e)

    def get_volume(self, volume_id):
        """
        Returns EBS volume object representing volume_id.
        Raises exception.VolumeDoesNotExist if unsuccessful
        """
        try:
            return self.conn.get_all_volumes(
                filters={'volume-id': volume_id})[0]
        except boto.exception.EC2ResponseError, e:
            self.__check_for_auth_failure(e)
            raise exception.VolumeDoesNotExist(volume_id)
        except IndexError:
            raise exception.VolumeDoesNotExist(volume_id)

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
                pbar.update(progress)
            except ValueError:
                time.sleep(5)
                continue
            time.sleep(refresh_interval)
        pbar.finish()

    def create_snapshot(self, vol, description=None, wait_for_snapshot=False,
                        refresh_interval=30):
        log.info("Creating snapshot of volume: %s" % vol.id)
        snap = vol.create_snapshot(description)
        if wait_for_snapshot:
            self.wait_for_snapshot(snap, refresh_interval)
        return snap

    def get_snapshots(self, volume_ids=[]):
        """
        Returns a list of all EBS volume snapshots for this account
        """
        filters = {}
        if volume_ids:
            filters['volume-id'] = volume_ids
        try:
            return self.conn.get_all_snapshots(owner='self', filters=filters)
        except boto.exception.EC2ResponseError, e:
            self.__check_for_auth_failure(e)

    def get_snapshot(self, snapshot_id):
        """
        Returns EBS snapshot object representing snapshot_id.
        Raises exception.SnapshotDoesNotExist if unsuccessful
        """
        try:
            return self.conn.get_all_snapshots(snapshot_ids=[snapshot_id])[0]
        except boto.exception.EC2ResponseError, e:
            self.__check_for_auth_failure(e)
            raise exception.SnapshotDoesNotExist(snapshot_id)
        except IndexError:
            raise exception.SnapshotDoesNotExist(snapshot_id)

    def get_volume_or_none(self, volume_id):
        """
        Returns EBS volume object representing volume_id.
        Returns none if unsuccessful
        """
        try:
            return self.get_volume(volume_id)
        except:
            pass

    def list_volumes(self, volume_id=None, status=None,
                     attach_status=None, size=None, zone=None,
                     snapshot_id=None, show_deleted=False):
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
                print
        print 'Total: %s' % len(vols)

    def get_spot_history(self, instance_type, start=None, end=None, plot=False,
                         plot_server_interface="localhost",
                         plot_launch_browser=True, plot_web_browser=None,
                         plot_shutdown_server=True):
        if start and not utils.is_iso_time(start):
            raise exception.InvalidIsoDate(start)
        if end and not utils.is_iso_time(end):
            raise exception.InvalidIsoDate(end)
        pdesc = "Linux/UNIX"
        hist = self.conn.get_spot_price_history(start_time=start, end_time=end,
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
        log.info("Current price: $%.2f" % prices[-1])
        log.info("Max price: $%.2f" % maximum)
        log.info("Average price: $%.2f" % avg)
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
                           start=start, end=end,
                           time_series_data=str(data),
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
        console_output = instance.get_console_output().output
        print ''.join([c for c in console_output if c in string.printable])


class EasyS3(EasyAWS):
    DefaultHost = 's3.amazonaws.com'
    _calling_format = boto.s3.connection.OrdinaryCallingFormat()

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 aws_s3_path='/', aws_port=None, aws_is_secure=True,
                 aws_s3_host=DefaultHost, cache=False, **kwargs):
        kwargs = dict(is_secure=aws_is_secure,
                      host=aws_s3_host or self.DefaultHost,
                      port=aws_port,
                      path=aws_s3_path)
        if aws_s3_host:
            kwargs.update(dict(calling_format=self._calling_format))
        super(EasyS3, self).__init__(aws_access_key_id, aws_secret_access_key,
                                     boto.connect_s3, **kwargs)
        self.cache = cache

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
        except boto.exception.S3CreateError, e:
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
        except boto.exception.S3ResponseError, e:
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
