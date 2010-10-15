#!/usr/bin/env python
"""
StarCluster Exception Classes
"""

import os

from starcluster import static
from starcluster.logger import log
from starcluster.templates import config


class BaseException(Exception):
    def __init__(self, *args):
        self.msg = args[0]

    def __str__(self):
        return self.msg

    def explain(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)


class CommandNotFound(BaseException):
    """Raised when command is not found on the system's PATH """
    def __init__(self, cmd):
        self.msg = "command not found: '%s'" % cmd


class RemoteCommandNotFound(CommandNotFound):
    """Raised when command is not found on a *remote* system's PATH """
    def __init__(self, cmd):
        self.msg = "command not found on remote system: '%s'" % cmd


class SSHError(BaseException):
    """Base class for all SSH related errors"""


class SSHConnectionError(SSHError):
    """Raised when ssh fails to to connect to a host (socket error)"""
    def __init__(self, host, port):
        self.msg = "failed to connect to host %s on port %s" % (host, port)


class SSHAuthException(SSHError):
    """Raised when an ssh connection fails to authenticate"""
    def __init__(self, user, host):
        self.msg = "failed to authenticate to host %s as user %s" % (user,
                                                                     host)


class SSHNoCredentialsError(SSHError):
    def __init__(self, *args):
        self.msg = "No password or key specified"


class AWSError(BaseException):
    """Base exception for all AWS related errors"""


class RegionDoesNotExist(AWSError):
    def __init__(self, region_name):
        self.msg = "region %s does not exist" % region_name


class AMIDoesNotExist(AWSError):
    def __init__(self, image_id):
        self.msg = "AMI %s does not exist" % image_id


class InstanceDoesNotExist(AWSError):
    def __init__(self, instance_id, label='instance'):
        self.msg = "%s '%s' does not exist" % (label, instance_id)


class InstanceNotRunning(AWSError):
    def __init__(self, instance_id, state, label='instance'):
        self.msg = "%s %s is not running (%s)" % (label, instance_id, state)


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


class SnapshotDoesNotExist(AWSError):
    def __init__(self, snap_id):
        self.msg = "snapshot %s does not exist" % snap_id


class RegionDoesNotExist(AWSError):
    def __init__(self, region):
        self.msg = "region %s does not exist" % region


class BucketDoesNotExist(AWSError):
    def __init__(self, bucket_name):
        self.msg = "bucket '%s' does not exist" % bucket_name


class InvalidOperation(AWSError):
    pass


class InvalidBucketName(AWSError):
    def __init__(self, bucket_name):
        self.msg = "bucket name %s is not valid" % bucket_name


class InvalidImageName(AWSError):
    def __init__(self, image_name):
        self.msg = "image name %s is not valid" % image_name


class AWSUserIdRequired(AWSError):
    def __init__(self):
        self.msg = "No Amazon user id specified in config (AWS_USER_ID)"


class EC2CertRequired(AWSError):
    def __init__(self):
        self.msg = "No certificate file (pem) specified in config (EC2_CERT)"


class EC2PrivateKeyRequired(AWSError):
    def __init__(self):
        self.msg = "No private certificate file (pem) file specified in " + \
                   "config (EC2_PRIVATE_KEY)"


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
        if len(defaults) == 2:
            tmpl_list = ' and '.join(defaults)
        else:
            first = defaults[0:-1]
            last = defaults[-1]
            tmpl_list = ', and '.join([', '.join(first), last])
        self.msg = msg % tmpl_list


class NoDefaultTemplateFound(ConfigError):
    def __init__(self, options=None):
        msg = "No default cluster template specified. To set the default "
        msg += "cluster template, set DEFAULT_TEMPLATE in the [global] section"
        msg += " of the config to the name of one of your cluster templates "
        if options:
            msg += '(' + ', '.join(options) + ')'
        self.msg = msg


class ConfigNotFound(ConfigError):
    def __init__(self, *args, **kwargs):
        self.msg = args[0]
        self.cfg = args[1]
        self.template = config.copy_paste_template

    def create_config(self):
        cfg_parent_dir = os.path.dirname(self.cfg)
        if not os.path.exists(cfg_parent_dir):
            os.makedirs(cfg_parent_dir)
        cfg_file = open(self.cfg, 'w')
        cfg_file.write(config.config_template)
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
    """Raised when creating/loading a cluster receipt fails"""


class ClusterValidationError(ValidationError):
    """Cluster validation related errors"""


class IncompatibleSettings(ClusterValidationError):
    """Raised when two or more settings conflict with each other"""


class InvalidProtocol(ClusterValidationError):
    """Raised when user specifies an invalid IP protocol for permission"""
    def __init__(self, protocol):
        self.msg = "protocol %s is not a valid ip protocol. options: %s" % \
        (protocol, ', '.join(static.PROTOCOLS))


class InvalidPortRange(ClusterValidationError):
    """Raised when user specifies an invalid port range for permission"""
    def __init__(self, from_port, to_port, reason=None):
        self.msg = ''
        if reason:
            self.msg += "%s\n" % reason
        self.msg += "port range is invalid: from %s to %s" % (from_port,
                                                              to_port)


class InvalidCIDRSpecified(ClusterValidationError):
    """Raised when user specifies an invalid CIDR ip for permission"""
    def __init__(self, cidr):
        self.msg = "cidr_ip is invalid: %s" % cidr


class InvalidZone(ClusterValidationError):
    """
    Raised when a zone has been specified that does not match the common
    zone of the volumes being attached
    """
    def __init__(self, zone, common_vol_zone):
        cvz = common_vol_zone
        self.msg = ("availability_zone setting '%s' does not " +
                    "match the common volume zone '%s'") % (zone, cvz)


class VolumesZoneError(ClusterValidationError):
    def __init__(self, volumes):
        vlist = ', '.join(volumes)
        self.msg = 'Volumes %s are not in the same availability zone' % vlist


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
        self.msg += "\n\nIf you wish to use these existing instances " + \
                    "anyway, pass --no-create to the start command"


class CancelledStartRequest(BaseException):
    def __init__(self, tag):
        self.msg = "Request to start cluster '%s' was cancelled" % tag
        self.msg += "\n\nPlease be aware that instances may still be running."
        self.msg += "\nYou can check this from the output of:"
        self.msg += "\n\n   $ starcluster listclusters"
        self.msg += "\n\nIf you wish to destroy these instances please run:"
        self.msg += "\n\n   $ starcluster stop %s" % tag
        self.msg += "\n\nYou can then use:\n\n   $ starcluster listinstances"
        self.msg += "\n\nto verify that the instances have been terminated."
        self.msg += "\n\nAnother option is to use the AWS management console"
        self.msg += "\nto terminate the instances manually."
        self.msg += "\n\nIf you would like to re-use these instances, rerun"
        self.msg += "\nthe same start command with the --no-create option"


class CancelledCreateVolume(BaseException):
    def __init__(self):
        self.msg = "Request to create volume was cancelled"
        self.msg += "\n\nPlease be aware that the volume host instance"
        self.msg += "may still be running. "
        self.msg += "\n\nTo destroy this instance please run:"
        self.msg += "\n\n   $ starcluster stop %s" % static.VOLUME_GROUP_NAME
        self.msg += "\n\nand then use\n\n   $ starcluster listinstances"
        self.msg += "\n\nto verify that this instance has been terminated."
        self.msg += "\n\nAnother option is to use the AWS management console "
        self.msg += "to terminate\nthis instance manually."


class CancelledCreateImage(BaseException):
    def __init__(self, bucket, image_name):
        self.msg = "Request to createimage was cancelled"
        self.msg += "\n\nDepending on how far along the process was before it "
        self.msg += "was cancelled, \nsome intermediate files might still be "
        self.msg += "around in /mnt on the instance."
        self.msg += "\n\nAlso, some of these intermediate files might "
        self.msg += "have been uploaded to \nS3 in the '%(bucket)s' bucket "
        self.msg += "you specified. You can check this by running:"
        self.msg += "\n\n   $ starcluster showbucket %(bucket)s\n\n"
        self.msg += "and looking for files like: "
        self.msg += "'%(iname)s.manifest.xml' or '%(iname)s.part.*'"
        self.msg += "\nRe-executing the same creatimage command "
        self.msg += "should take care of these \nintermediate files and "
        self.msg += "will also automatically override any\npartially uploaded "
        self.msg += "files in S3."
        self.msg = self.msg % {'bucket': bucket, 'iname': image_name}


class ExperimentalFeature(BaseException):
    def __init__(self, feature_name):
        self.msg = "%s is an experimental feature for this " % feature_name
        self.msg += "release. \nIf you wish to test this feature, set "
        self.msg += "ENABLE_EXPERIMENTAL=True \nin the [global] section of the"
        self.msg += " config. \nYou have officially been warned :D"
