#!/usr/bin/env python
"""
StarCluster Exception Classes
"""
import os
from starcluster.logger import log
from starcluster.templates.config import config_template, copy_paste_template

class BaseException(Exception):
    def __init__(self, *args):
        self.msg = args[0]
    def __str__(self):
        return self.msg
    def explain(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)

class AWSError(BaseException):
    pass

class AMIDoesNotExist(AWSError):
    def __init__(self, image_id):
        self.msg = "AMI %s does not exist" % image_id

class InstanceDoesNotExist(AWSError):
    def __init__(self, instance_id):
        self.msg = "instance %s does not exist" % instance_id

class SecurityGroupDoesNotExist(AWSError):
    def __init__(self, sg_name):
        self.msg = "security group %s does not exist" % sg_name

class KeyPairDoesNotExist(AWSError):
    def __init__(self, keyname):
        self.msg = "keypair %s does not exist" % keyname

class ZoneDoesNotExist(AWSError):
    def __init__(self, zone):
        self.msg = "zone %s does not exist" % zone

class VolumeDoesNotExist(AWSError):
    def __init__(self, vol_id):
        self.msg = "volume %s does not exist" % vol_id

class InstanceNotRunning(AWSError):
    def __init__(self, instance_id):
        self.msg = "instance %s is not running" % instance_id

class InvalidBucketName(AWSError):
    def __init__(self, bucket_name):
        self.msg = "bucket name %s is not valid" % bucket_name 

class InvalidImageName(AWSError):
    def __init__(self, image_name):
        self.msg = "image name %s is not valid" % image_name

class EC2CertRequired(AWSError):
    def __init__(self):
        self.msg = "No certificate file (pem) file specified"

class EC2PrivateKeyRequired(AWSError):
    def __init__(self):
        self.msg = "No certificate file (pem) file specified"

class EC2CertDoesNotExist(AWSError):
    def __init__(self, key):
        self.msg = "EC2 certificate file %s does not exist" % key

class EC2PrivateKeyDoesNotExist(AWSError):
    def __init__(self, key):
        self.msg = "EC2 private key file %s does not exist" % key

class ConfigError(BaseException):
    """Base class for all config related errors"""

class ConfigSectionMissing(ConfigError):
    pass

class ConfigNotFound(ConfigError):
    def __init__(self, *args, **kwargs):
        super(ConfigNotFound, self).__init__(*args, **kwargs)
        self.cfg = args[1]
        self.template = copy_paste_template

    def create_config(self):
        cfg_parent_dir = os.path.dirname(self.cfg)
        if not os.path.exists(cfg_parent_dir):
            os.makedirs(cfg_parent_dir)
        cfg_file = open(self.cfg, 'w')
        cfg_file.write(config_template)
        cfg_file.close()
        log.info("Config template written to %s. Please customize this file." %
                 self.cfg)

    def display_options(self):
        print 'Options:'
        print '--------' 
        print '[1] Show the StarCluster config template'
        print '[2] Write config template to %s' % self.cfg
        print '[q] Quit'
        resp = raw_input('\nPlase enter your selection: ')
        if resp == '1':
            print self.template
        elif resp == '2':
            print
            self.create_config()

class KeyNotFound(ConfigError):
    def __init__(self, keyname):
        self.msg = "key %s not found in config" % keyname

class PluginError(BaseException):
    """Base class for plugin errors"""

class PluginLoadError(PluginError):
    """Raised when an error is encountered while loading a plugin"""

class PluginSyntaxError(PluginError):
    """Raised when plugin contains syntax errors"""

class ValidationError(BaseException):
    """Base class for validation related errors"""

class ClusterReceiptError(BaseException):
    """Raised when Cluster class fails to create a receipt on the master node"""

class ClusterValidationError(ValidationError):
    """Cluster validation related errors"""

class IncompatibleSettings(ClusterValidationError):
    """Raised when two or more settings conflict with each other"""

class ClusterTemplateDoesNotExist(BaseException):
    """
    Exception raised when user requests a cluster template that does not exist
    """
    def __init__(self, cluster_name):
        self.msg = "cluster template %s does not exist" % cluster_name

class ClusterDoesNotExist(BaseException):
    """
    Exception raised when user requests a running cluster that does not exist
    """
    def __init__(self, cluster_name):
        self.msg = "cluster %s does not exist" % cluster_name
