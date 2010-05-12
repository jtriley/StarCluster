#!/usr/bin/env python
"""
StarCluster Exception Classes
"""
import os
from starcluster import static
from starcluster.logger import log
from starcluster.templates.config import config_template, copy_paste_template

class BaseException(Exception):
    def __init__(self, *args):
        self.msg = args[0]
    def __str__(self):
        return self.msg
    def explain(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)

class SSHError(BaseException):
    """Base class for all SSH related errors"""

class SSHConnectionError(SSHError):
    """Raised when ssh fails to to connect to a host (socket error)"""
    def __init__(self, host, port):
        self.msg = "failed to connect to host %s on port %s" % (host,port)

class SSHAuthException(SSHError):
    """Raised when an ssh connection fails to authenticate"""
    def __init__(self, user, host):
        self.msg = "failed to authenticate to host %s as user %s" % (user, host)

class SSHNoCredentialsError(BaseException):
    def __init__(self, *args):
        self.msg = "No password or key specified"

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

class SpotHistoryError(AWSError):
    def __init__(self, start, end):
        self.msg = "no spot price history for the dates specified: " + \
                "%s - %s" % (start, end)

class InvalidIsoDate(BaseException):
    def __init__(self, date):
        self.msg = "Invalid date specified: %s" % date

class ConfigError(BaseException):
    """Base class for all config related errors"""

class ConfigSectionMissing(ConfigError):
    pass

class ConfigHasNoSections(ConfigError):
    def __init__(self, cfg_file):
        self.msg = "No valid sections defined in config file %s" % cfg_file

class PluginNotFound(ConfigError):
    def __init__(self, plugin):
        self.msg = 'Plugin "%s" not found in config' % plugin

class MultipleDefaultTemplates(ConfigError):
    def __init__(self, defaults):
        msg = 'Cluster templates %s each have DEFAULT=True in your config.'
        msg += ' Only one cluster can be the default. Please pick one.'
        l = ''
        if len(defaults) == 2:
            tmpl_list = ' and '.join(defaults)
        else:
            first = defaults[0:-1]
            last = defaults[-1]
            tmpl_list = ', and '.join([', '.join(first), last])
        self.msg = msg % tmpl_list

class NoDefaultTemplateFound(ConfigError):
    def __init__(self, options=None):
        msg = "No default cluster template specified. To set the default cluster "
        msg += "template, set DEFAULT_TEMPLATE in the [global] section "
        msg += "of the config to the name of one of your cluster templates "
        if options:
            msg +='(' + ', '.join(options) + ')'
        self.msg = msg

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

class InvalidDevice(BaseException):
    def __init__(self, device):
        self.msg = "invalid device specified: %s" % device

class InvalidPartition(BaseException):
    def __init__(self, part):
        self.msg = "invalid partition specified: %s" % part

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

class InvalidZone(ClusterValidationError):
    """Raised when user specified a zone that is not the same as the zone of the
    volumes being attached"""
    def __init__(self, zone, common_vol_zone):
        self.msg = "zone %s does not match common volume zone %s" % (zone, common_vol_zone)

class VolumesZoneError(ClusterValidationError):
    def __init__(self, volumes):
        self.msg = 'Volumes %s are not in the same availability zone' % ', '.join(volumes)

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

class ClusterExists(BaseException):
    def __init__(self, cluster_name):
        self.msg = "Cluster with tag name %s already exists. " % cluster_name
        self.msg += "\n\nEither choose a different tag name, or stop the "
        self.msg += "existing cluster using:"
        self.msg += "\n\n   $ starcluster stop %s" % cluster_name
        self.msg += "\n\nIf you wish to use these existing instances anyway, " + \
                    "pass --no-create to the start command"

class CancelledStartRequest(BaseException):
    def __init__(self, tag):
        self.msg = "Request to start cluster '%s' was cancelled" % tag
        self.msg += "\n\nPlease be aware that instances may still be running. "
        self.msg += "\nYou can check this from the output of:"
        self.msg += "\n\n   $ starcluster listclusters"
        self.msg += "\n\nIf you wish to destroy these instances please run:"
        self.msg += "\n\n   $ starcluster stop %s"  % tag
        self.msg += "\n\nYou can then use:\n\n   $ starcluster listinstances"
        self.msg += "\n\nto verify that the instances have been terminated."
        self.msg += "\n\nAnother option is to use the AWS management console to"
        self.msg += "\nterminate the instances manually."
        self.msg += "\n\nIf you would like to re-use these instances, rerun the"
        self.msg += "\nsame start command with the --no-create option"

class CancelledCreateVolume(BaseException):
    def __init__(self):
        self.msg = "Request to create volume was cancelled"
        self.msg += "\n\nPlease be aware that the volume host instance may still"
        self.msg += " be running. "
        self.msg += "\n\nTo destroy this instance please run:"
        self.msg += "\n\n   $ starcluster stop %s" % static.VOLUME_GROUP_NAME
        self.msg += "\n\nand then use\n\n   $ starcluster listinstances"
        self.msg += "\n\nto verify that this instance has been terminated."
        self.msg += "\n\nAnother option is to use the AWS management console to"
        self.msg += "\nterminate this instance manually."

class CancelledCreateImage(BaseException):
    def __init__(self, bucket, image_name):
        self.msg = "Request to createimage was cancelled"
        self.msg += "\n\nDepending on how far along the process was before it "
        self.msg += "was cancelled, \nsome intermediate files might still be "
        self.msg += "around in /mnt on the instance. "
        self.msg += "\n\nAlso, some of these intermediate files "
        self.msg += "might have been uploaded to S3 in the '%s' bucket" % bucket
        self.msg += "\nyou specified. You can check this by running: "
        self.msg += "\n\n   $ starcluster showbucket %s\n\n" % bucket
        self.msg += "and looking for files like '%s.manifest.xml' " % image_name
        self.msg += "or '%s.part.*'" % image_name 
        self.msg += "\nRe-executing the same creatimage command should take care "
        self.msg += "of these \nintermediate files and will also automatically "
        self.msg += "override any partially uploaded files in S3." 

class ExperimentalFeature(BaseException):
    def __init__(self, feature_name):
        self.msg = "%s is an experimental feature for this " % feature_name
        self.msg += "release. \nIf you wish to test this feature, set "
        self.msg += "ENABLE_EXPERIMENTAL=True \nin the [global] section of the "
        self.msg += "config. \nYou have officially been warned :D"
