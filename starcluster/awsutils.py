#!/usr/bin/env python
""" 
EC2/S3 Utility Classes
"""

import os
import time
import sys
import platform
from pprint import pprint

import boto
import boto.ec2
import boto.s3
from starcluster import static
from starcluster.logger import log
from starcluster.utils import print_timing
from starcluster.hacks import register_image as _register_image

class EasyAWS(object):
    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 connection_authenticator, **kwargs):
        """
        Create an EasyAWS object. 

        Requires AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY from an Amazon Web 
        Services (AWS) account and a CONNECTION_AUTHENTICATOR function that 
        returns an authenticated AWS connection object

        Providing only the keys will default to using Amazon EC2

        kwargs are passed to the connection_authenticator constructor
        """
        self.aws_access_key = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.connection_authenticator = connection_authenticator
        self._conn = None
        self._kwargs = kwargs

    @property
    def conn(self):
        if self._conn is None:
            log.debug('creating self._conn w/ connection_authenticator kwargs' +
                      ' = %s' % self._kwargs)
            self._conn = self.connection_authenticator(
                self.aws_access_key, self.aws_secret_access_key, **self._kwargs
            )
        return self._conn


class EasyEC2(EasyAWS):
    def __init__(self, aws_access_key_id, aws_secret_access_key, aws_ec2_path='/',
                 aws_s3_path='/', aws_port=None, aws_region_name=None, 
                 aws_is_secure=True, aws_region_host=None, cache=False, **kwargs):
        aws_region = None
        if aws_region_name and aws_region_host:
            aws_region = boto.ec2.regioninfo.RegionInfo(name=aws_region_name, 
                                                        endpoint=aws_region_host)
        kwargs = dict(is_secure=aws_is_secure, region=aws_region, 
                      port=aws_port, path=aws_ec2_path)
        super(EasyEC2, self).__init__(aws_access_key_id, aws_secret_access_key, 
                                      boto.connect_ec2, **kwargs)

        kwargs = dict(aws_s3_path=aws_s3_path, aws_port=aws_port,
                      aws_is_secure=aws_is_secure,
                      cache=cache)
        if aws_region_host:
            kwargs.update(dict(aws_region_host=aws_region_host))
        self.s3 = EasyS3(aws_access_key_id, aws_secret_access_key, **kwargs)
        self.cache = cache
        self._instance_response = None
        self._keypair_response = None
        self._images = None
        self._security_group_response = None

    @property
    def registered_images(self):
        if not self.cache or self._images is None:
            self._images = self.conn.get_all_images(owners=["self"])
        return self._images

    def get_registered_image(self, image_id):
        if not image_id.startswith('ami') or len(image_id) != 12:
            raise TypeError("invalid AMI name/id requested: %s" % image_id)
        for image in self.registered_images:
            if image.id == image_id:
                return image

    def create_group(self, name, description, auth_ssh=True,
                     auth_group_traffic=False):
        if not name:
            return None
        log.info("Creating security group %s..." % name)
        sg = self.conn.create_security_group(name, description)
        if auth_ssh:
            sg.authorize('tcp', 22, 22, '0.0.0.0/0')
        if auth_group_traffic:
            sg.authorize(src_group=self.get_group_or_none(name))
        return sg

    def get_group_or_none(self, name):
        try:
            sg = self.conn.get_all_security_groups(groupnames=[name])[0]
            return sg
        except boto.exception.EC2ResponseError, e:
            pass
        except IndexError, e:
            pass

    def get_or_create_group(self, name, description, auth_ssh=True, auth_group_traffic=False):
        """ 
        Try to return a security group by name.
        If the group is not found, attempt to create it. 
        Description only applies to creation.

        Authorizes all traffic between members of the group
        """
        sg = self.get_group_or_none(name)
        if not sg:
            sg = self.create_group(name, description, auth_ssh,
                                     auth_group_traffic)
        return sg

    def run_instances(self, image_id, instance_type='m1.small', min_count=1,
                      max_count=1, key_name=None, security_groups=None,
                      placement=None):
        return self.conn.run_instances(image_id, instance_type=instance_type,
                                       min_count=min_count,
                                      max_count=max_count, key_name=key_name,
                                       security_groups=security_groups,
                                      placement=placement)

    def register_image(self, name, description=None, image_location=None,
                       architecture=None, kernel_id=None, ramdisk_id=None,
                       root_device_name=None, block_device_map=None):
        return _register_image(self.conn, name, description, image_location,
                           architecture, kernel_id, ramdisk_id,
                           root_device_name, block_device_map)

    def get_keypair(self, keypair):
        return self.conn.get_all_key_pairs(keynames=[keypair])[0]

    def __print_header(self, msg):
        print msg
        print "-" * len(msg)

    def get_image_name(self, img):
        return img.location.split('/')[1].split('.manifest.xml')[0]

    def get_instance(self, instance_id):
        try:
            res = self.conn.get_all_instances(instance_ids=[instance_id])
            return res[0].instances[0]
        except boto.exception.EC2ResponseError,e:
            pass
        except IndexError,e:
            # for eucalyptus, invalid instance_id returns []
            pass

    def get_all_instances(self, instance_ids=[]):
        reservations = self.conn.get_all_instances(instance_ids)
        instances = []
        for res in reservations:
            instances.extend(res.instances)
        return instances

    def list_all_instances(self):
        reservations = self.conn.get_all_instances()
        if not reservations:
            log.info("No instances found")
        for res in reservations:
            groups = ', '.join([ g.id for g in res.groups]) or 'N/A'
            for instance in res.instances:
                id = instance.id or 'N/A'
                dns_name = instance.dns_name or 'N/A'
                state = instance.state or 'N/A'
                private_ip = instance.private_ip_address or 'N/A'
                public_ip = instance.ip_address or 'N/A'
                zone = instance.placement or 'N/A'
                ami = instance.image_id or 'N/A'
                keypair = instance.key_name or 'N/A'
                print "id: %s" % id
                print "dns_name: %s" % dns_name
                print "state: %s" % state
                print "public ip: %s" % public_ip 
                print "private_ip: %s" % private_ip
                print "zone: %s" % zone
                print "ami: %s" % ami
                print "groups: %s" % groups
                print "keypair: %s" % keypair
                print
            
    def list_registered_images(self):
        images = self.registered_images
        def get_key(obj):
            return str(obj.region) + ' ' + str(obj.location)
        imgs_i386 = [ img for img in images if img.architecture == "i386" ]
        imgs_i386.sort(key=get_key)
        imgs_x86_64 = [ img for img in images if img.architecture == "x86_64" ]
        imgs_x86_64.sort(key=get_key)
        self.__list_images("Your 32bit Images:", imgs_i386)
        self.__list_images("\nYour 64bit Images:", imgs_x86_64)
        print "\ntotal registered images: %d" % len(images)

    def __list_images(self, msg, imgs):
        counter = 0
        self.__print_header(msg)
        for image in imgs:
            name = self.get_image_name(image)
            print "[%d] %s %s %s" % (counter, image.id, image.region.name, name)
            counter += 1

    def remove_image_files(self, image_name, pretend=True):
        image = self.get_image(image_name)
        if image is None:
            log.error('cannot remove AMI %s' % image_name)
            return
        bucket = os.path.dirname(image.location)
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

    @print_timing
    def remove_image(self, image_name, pretend=True):
        image = self.get_image(image_name)
        if image is None:
            log.error('AMI %s does not exist' % image_name)
            return
        if pretend:
            log.info("Pretending to remove AMI: %s" % imageid)
        else:
            log.info("Removing AMI: %s" % image_name)

        # first remove image files
        log.info('Removing image files...')
        self.remove_image_files(image_name, pretend = pretend)

        # then deregister ami
        ami = image.id
        if pretend:
            log.info('Would run deregister_image for ami: %s)' % ami)
        else:
            log.info('Deregistering ami: %s' % ami)
            self.conn.deregister_image(ami)

    def list_image_files(self, image_name, bucket=None):
        files = self.get_image_files(image_name, bucket)
        for file in files:
            print file

    def get_zone(self, zone):
        try:
            return self.conn.get_all_zones(zones=[zone])[0]
        except IndexError,e:
            return None

    def get_image(self, image_id):
        try:
            return self.conn.get_all_images(image_ids=[image_id])[0]
        except IndexError,e:
            return None

    def get_image_files(self, image_id):
        image = self.get_image(image_id)
        bucketname = image.location.split('/')[0]
        bucket = self.s3.get_bucket(bucketname)
        files = bucket.list(prefix=os.path.basename(image.location).split('.manifest.xml')[0])
        # boto with eucalyptus returns boto.s3.prefix.Prefix class at the 
        # end of the list, we ignore these by checking for delete method
        files = [ file for file in files if hasattr(file,'delete')]
        return files

    def list_image_files(self, image_id):
        files = self.get_image_files(image_id)
        for file in files:
            print file.name

    @property
    def instances():
        if not self.cache or self._instance_response is None:
            log.debug('instance_response = %s, cache = %s' %
            (self._instance_response, self.cache))
            self._instance_response=self.conn.get_all_instances()
        return self._instance_response
            
    @property
    def keypair():
        if not self.cache or self._keypair_response is None:
            log.debug('keypair_response = %s, cache = %s' %
            (self._keypair_response, self.cache))
            self._keypair_response = self.conn.get_all_keypairs()
        return self._keypair_response

    def get_running_instances(self):
        """ 
        TODO: write me 
        """
        pass

    def terminate_instances(self, instances=None):
        if instances:
            self.conn.terminate_instances(instances)

    def get_volumes(self):
        return self.conn.get_all_volumes()

    def get_volume(self, volume_id):
        return self.conn.get_all_volumes(volume_ids=[volume_id])[0]

    def list_volumes(self):
        vols = self.get_volumes()
        if vols:
            for vol in vols:
                print "volume_id: %s" % vol.id
                print "size: %sGB" % vol.size
                print "status: %s" % vol.status
                print "availability_zone: %s" % vol.zone
                if vol.snapshot_id:
                    print "snapshot_id: %s" % vol.snapshot_id
                snapshots=vol.snapshots()
                if snapshots:
                    print 'snapshots: %s' % ' '.join([snap.id for snap in snapshots])
                print

    def get_security_group(self, groupname):
        return self.conn.get_all_security_groups(groupnames=[groupname])[0]

    def get_security_groups(self):
        return self.conn.get_all_security_groups()

class EasyS3(EasyAWS):
    DefaultHost = 's3.amazonaws.com'
    _calling_format=boto.s3.connection.OrdinaryCallingFormat()
    def __init__(self, aws_access_key_id, aws_secret_access_key,  
                 aws_s3_path='/', aws_port=None, aws_is_secure=True, 
                 aws_region_host=DefaultHost, cache=False, **kwargs):
        kwargs = dict(is_secure=aws_is_secure, host=aws_region_host, 
                      calling_format=self._calling_format, port=aws_port, 
                      path=aws_s3_path)
        super(EasyS3, self).__init__(aws_access_key_id, aws_secret_access_key,
                                     boto.connect_s3, **kwargs)
        self.cache = cache

    def bucket_exists(self, bucket_name):
        try:
            self.conn.get_bucket(bucket_name)
            return True
        except boto.exception.S3ResponseError,e:
            log.error('bucket %s does not exist' % bucket_name)
            return False

    def get_bucket_or_none(self, bucket_name):
        try:
            return self.conn.get_bucket(bucket_name)
        except boto.exception.S3ResponseError,e:
            pass

    def get_bucket(self, bucketname):
        return self.conn.get_bucket(bucketname)

    def list_bucket(self, bucketname):
        bucket = self.get_bucket_or_none(bucketname)
        if bucket:
            for file in bucket.list():
                if file.name: print file.name
        else:
            log.error('bucket %s does not exist' % bucketname)

    def get_buckets(self):
        buckets = self.conn.get_all_buckets()
        return buckets

    def list_buckets(self):
        for bucket in self.get_buckets():
            print bucket.name

    def get_bucket_files(self, bucketname):
        files = []
        try:
            bucket = self.get_bucket(bucketname)
        except:
            return 
        if self.bucket_exists(bucket_name):
            files = [ entry.key for entry in self.conn.list_bucket(bucket_name).entries] 
        else:
            files = []
        return files

    def show_bucket_files(self, bucket_name):
        if self.bucket_exists(bucket_name):
            files = self.get_bucket_files(bucket_name)
            for file in files:
                print file

if __name__ == "__main__":
    from starcluster.config import get_easy_ec2
    ec2 = get_easy_ec2()
    ec2.list_all_instances()
    #ec2.list_registered_images()
