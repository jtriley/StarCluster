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
import config 
import static
from logger import log

class EasyAWS(object):
    def __init__(self, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, CONNECTION_AUTHENTICATOR):
        """
        Create an EasyAWS object. 

        Requires AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY from an Amazon Web Services (AWS) account
        and a CONNECTION_AUTHENTICATOR function that returns an
        authenticated AWS connection object
        """

        #log.info('aws_access_key = %s' % AWS_ACCESS_KEY_ID)
        #log.info('aws_secret_access_key = %s' % AWS_SECRET_ACCESS_KEY)
        self.aws_access_key = AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = AWS_SECRET_ACCESS_KEY
        self.connection_authenticator = CONNECTION_AUTHENTICATOR
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            log.debug('creating self._conn')
            self._conn = self.connection_authenticator(self.aws_access_key,
                self.aws_secret_access_key)
        return self._conn

def get_easy_ec2(**kwargs):
    """
    Factory for EasyEC2 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyEC2 object if
    successful.
    """
    if kwargs:
        return EasyEC2(**kwargs)
    cfg = config.StarClusterConfig(); cfg.load()
    ec2 = EasyEC2(**cfg.aws)
    return ec2

class EasyEC2(EasyAWS):
    def __init__(self, AWS_ACCESS_KEY_ID=None, AWS_SECRET_ACCESS_KEY=None, cache=False, **kwargs):
        super(EasyEC2, self).__init__(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, boto.connect_ec2)
        self.cache = cache
        self._instance_response = None
        self._keypair_response = None
        self._images = None
        self._security_group_response = None
        self.s3 = EasyS3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, cache, **kwargs)

    @property
    def registered_images(self):
        if not self.cache or self._images is None:
            self._images = self.conn.get_all_images(owners=["self"])
        return self._images

    def get_registered_image(self, image_id):
        if not image_name.startswith('ami') or len(image_name) != 12:
            raise TypeError("invalid AMI name/id requested: %s" % image_name)
        for image in self.registered_images:
            if image.id == image_id:
                return image

    def get_group_or_none(self, name):
        try:
            sg = self.conn.get_all_security_groups(group_names=[name])[0]
            return sg
        except boto.exception.EC2ResponseError, e:
            pass

    def get_or_create_group(self, name, description):
        """ 
        Try to return a security group by name.
        If the group is not found, attempt to create it. 
        Description only applies to creation.

        Authorizes ssh port 22 by default if creating a new group
        """
        try:
            sg = self.conn.get_all_security_groups(
                groupnames=[name])[0]
            return sg
        except boto.exception.EC2ResponseError, e:
            if not name:
                return None
            log.info("Creating security group %s..." % name)
            sg = self.conn.create_security_group(name, description)
            sg.authorize('tcp', 22, 22,'0.0.0.0/0')
            return sg
            
    def list_registered_images(self):
        images = self.registered_images
        for image in images:
            name = os.path.basename(image.location).split('.manifest.xml')[0]
            bucket = os.path.dirname(image.location)
            metadata = dict(NAME=name, AMI=image.id, BUCKET=bucket,
                            MANIFEST=image.location) 
            pprint(metadata)

    def remove_image_files(self, image_name, bucket=None, pretend=True):
        image = self.get_image(image_name)
        if image is None:
            log.error('cannot remove AMI %s' % image_name)
            return
        bucket = image['BUCKET']
        files = self.get_image_files(image_name, bucket)
        for file in files:
            if pretend:
                print file
            else:
                print 'removing file %s' % file
                self.s3.remove_file(bucket, file)

        # recursive double check
        files = get_image_files(image_name, bucket)
        if len(files) != 0:
            if pretend:
                log.debug('not all files deleted, would recurse')
            else:
                log.debug('not all files deleted, recursing')
                self.remove_image_files(image_name, bucket, pretend)
        

    def remove_image(self, image_name, pretend=True):
        image = self.get_image(image_name)
        if image is None:
            log.error('cannot remove AMI %s' % image_name)
            return

        # first remove image files
        self.remove_image_files(image_name, pretend = pretend)

        # then deregister ami
        name = image['NAME']
        ami = image['AMI']
        if pretend:
            log.info('Would run conn.deregister_image for image %s (ami: %s)' % (name,ami))
        else:
            log.info('Removing image %s (ami: %s)' % (name,ami))
            self.conn.deregister_image(ami)

    def list_image_files(self, image_name, bucket=None):
        files = self.get_image_files(image_name, bucket)
        for file in files:
            print file

    def get_image(self, image_id):
        return self.conn.get_all_images(image_ids=[image_id])[0]

    def get_image_files(self, image_id):
        image = self.get_image(image_id)
        bucketname = image.location.split('/')[0]
        bucket = self.s3.get_bucket(bucketname)
        files = bucket.list(prefix=image.location.split('/')[1].split('.manifest.xml')[0])
        return files

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
        if instances is not None:
            self.conn.terminate_instances(instances)

    def get_volumes(self):
        return self.conn.get_all_volumes()

    def get_volume(self, volume_id):
        return self.conn.get_all_volumes(volume_ids=[volume])

    def list_volumes(self):
        vols = self.get_volumes()
        if vols is not None:
            for vol in vols:
                print vol

    def get_security_group(self, groupname):
        return self.conn.get_all_security_groups(groupnames=[groupname])[0]

    def get_security_groups(self):
        return self.conn.get_all_security_groups()

def get_easy_s3(**kwargs):
    """
    Factory for EasyEC2 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyEC2 object if
    successful.
    """
    if kwargs:
        return EasyS3(**kwargs)
    cfg = config.StarClusterConfig(); cfg.load()
    s3 = EasyS3(**cfg.aws)
    return s3

class EasyS3(EasyAWS):
    def __init__(self, AWS_ACCESS_KEY_ID=None, AWS_SECRET_ACCESS_KEY=None, cache=False, **kwargs):
        super(EasyS3, self).__init__(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, boto.connect_s3)
        self.cache = cache

    def bucket_exists(self, bucket_name):
        exists = (self.conn.check_bucket_exists(bucket_name).reason == 'OK')
        if not exists:
            log.error('bucket %s does not exist' % bucket_name)
        return exists

    def get_bucket(self, bucketname):
        return self.conn.get_bucket(bucketname)

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

    def remove_file(self, bucket_name, file_name):
        self.conn.delete(bucket_name, file_name)

if __name__ == "__main__":
    ec2 = get_easy_ec2()
    ec2.list_registered_images()
