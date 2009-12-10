#!/usr/bin/env python
""" 
EC2/S3 Utility Classes
"""

import os
import sys
import platform

import S3
import EC2
import config 
from logger import log

class EasyAWS(object):
    def __init__(self, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, CONNECTION_AUTHENTICATOR):
        """
        Create an EasyAWS object. 

        Requires AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY from an Amazon Web Services (AWS) account
        and a CONNECTION_AUTHENTICATOR function that returns an
        authenticated AWS connection object
        """

        log.info('aws_access_key = %s' % AWS_ACCESS_KEY_ID)
        log.info('aws_secret_access_key = %s' % AWS_SECRET_ACCESS_KEY)
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
        super(EasyEC2, self).__init__(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, EC2.AWSAuthConnection)
        self.cache = cache
        self._instance_response = None
        self._keypair_response = None
        self._images = None
        self.s3 = EasyS3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, cache, **kwargs)

    @property
    def registered_images(self):
        if not self.cache or self._images is None:
            image_list = self.conn.describe_images(owners=["self"]).parse()
            images = {}
            for image in image_list:
                image_name = os.path.basename(image[2]).split('.manifest.xml')[0]
                images[image_name] = {}
                img_dict = images[image_name]
                img_dict['NAME'] = image_name
                img_dict['AMI'] = image[1]
                img_dict['MANIFEST'] = image[2] 
                img_dict['BUCKET'] = os.path.dirname(image[2])
                img_dict['STATUS'] = image[4] 
                img_dict['PRIVACY'] = image[5] 
            self._images = images
        return self._images

    def get_image(self, image_name):
        rimages = self.registered_images
        try:
            log.debug("attempting to fetch ami: %s" % image_name)
            return rimages[image_name]
        except:
            if image_name.startswith('ami') and len(image_name) == 12:
                for ami in rimages.itervalues():
                    if ami['AMI'] == image_name:
                        log.debug("returning ami: %s" % ami['AMI'])
                        return ami
            log.error("invalid AMI name/id specified: %s" % image_name)

    def list_registered_images(self):
        images = self.registered_images
        for image in images.keys():
            print "%(NAME)s AMI=%(AMI)s BUCKET=%(BUCKET)s MANIFEST=%(MANIFEST)s" % images[image]

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

    def get_image_files(self, image_name, bucket=None):
        image = self.get_image(image_name)
        if image is not None:
            # recreating image_name in case they passed ami id instead of human readable
            image_name = image['NAME']
            bucket_files = self.s3.get_bucket_files(image['BUCKET'])
            image_files = []
            for file in bucket_files:
                if file.split('.part.')[0] == image_name:
                    image_files.append(file)
            return image_files
        else:
            return []

    @property
    def instance_response(self):
        if not self.cache or self._instance_response is None:
            log.debug('instance_response = %s, cache = %s' %
            (self._instance_response, self.cache))
            self._instance_response=self.conn.describe_instances().parse()
        return self._instance_response
            
    @property
    def keypair_response(self):
        if not self.cache or self._keypair_response is None:
            log.debug('keypair_response = %s, cache = %s' %
            (self._keypair_response, self.cache))
            self._keypair_response = self.conn.describe_keypairs().parse()
        return self._keypair_response

    def get_running_instances(self, amis=[], strict=True):
        parsed_response = self.instance_response
        running_instances=[]
        for chunk in parsed_response:
            if chunk[0]=='INSTANCE' and chunk[5]=='running':
                if strict:
                    if chunk[2] in amis:
                        running_instances.append(chunk[1])
                else:
                    running_instances.append(chunk[1])
        return running_instances

    def get_external_hostnames(self):
        parsed_response=self.instance_response 
        external_hostnames = []
        if len(parsed_response) == 0:
            return external_hostnames        
        for chunk in parsed_response:
            #if chunk[0]=='INSTANCE' and chunk[-1]=='running':
            if chunk[0]=='INSTANCE' and chunk[5]=='running':
                external_hostnames.append(chunk[3])
        return external_hostnames

    def get_internal_hostnames(self):
        parsed_response=self.instance_response 
        internal_hostnames = []
        if len(parsed_response) == 0:
            return internal_hostnames
        for chunk in parsed_response:
            #if chunk[0]=='INSTANCE' and chunk[-1]=='running' :
            if chunk[0]=='INSTANCE' and chunk[5]=='running' :
                internal_hostnames.append(chunk[4])
        return internal_hostnames

    def get_instances(self, refresh=False):
        parsed_response = self.instance_response
        instances = []
        if len(parsed_response) != 0:
            for instance in parsed_response:
                if instance[0] == 'INSTANCE':
                    instances.append(instance)
        return instances

    def list_instances(self, refresh=False):
        instances = self.get_instances(refresh)
        if len(instances) != 0:
            counter = 0
            log.info("EC2 Instances:")
            for instance in instances:
                print "[%s] %s %s (%s)" % (counter, instance[3], instance[5],instance[2])
                counter +=1
        else:
            log.info("No instances found...")
        
    def terminate_instances(self, instances=None):
        if instances is not None:
            self.conn.terminate_instances(instances)

    def attach_volume_to_node(self, volume, node, device):
        return self.conn.attach_volume(volume, node, device).parse()

    def get_volumes(self):
        return self.conn.describe_volumes().parse()

    def get_volume(self, volume):
        return self.conn.describe_volumes([volume]).parse()

    def list_volumes(self):
        vols = self.get_volumes()
        if vols is not None:
            for vol in vols:
                print vol

    def detach_volume(self, volume):
        log.info("Detaching EBS device...")
        return self.conn.detach_volume(volume).parse()

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
        super(EasyS3, self).__init__(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3.AWSAuthConnection)
        self.cache = cache

    def bucket_exists(self, bucket_name):
        exists = (self.conn.check_bucket_exists(bucket_name).reason == 'OK')
        if not exists:
            log.error('bucket %s does not exist' % bucket_name)
        return exists

    def get_buckets(self):
        bucket_list = self.conn.list_all_my_buckets().entries
        buckets = []
        for bucket in bucket_list:
            buckets.append(bucket.name)
        return buckets

    def list_buckets(self):
        for bucket in self.get_buckets():
            print bucket

    def get_bucket_files(self, bucket_name):
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
