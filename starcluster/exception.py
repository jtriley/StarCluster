"""
StarCluster Exception Classes
"""

import os

from starcluster import static
from starcluster.logger import log
from starcluster.templates import config, user_msgs


class BaseException(Exception):
    def __init__(self, *args):
        self.args = args
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
        self.msg = "failed to authenticate to host %s as user %s" % (host,
                                                                     user)


class SSHNoCredentialsError(SSHError):
    def __init__(self):
        self.msg = "No password or key specified"


class SCPException(BaseException):
    """SCP exception class"""
    pass


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


class PlacementGroupDoesNotExist(AWSError):
    def __init__(self, pg_name):
        self.msg = "placement group %s does not exist" % pg_name


class KeyPairDoesNotExist(AWSError):
    def __init__(self, keyname):
        self.msg = "keypair %s does not exist" % keyname


class ZoneDoesNotExist(AWSError):
    def __init__(self, zone, region):
        self.msg = "zone %s does not exist in region %s" % (zone, region)


class VolumeDoesNotExist(AWSError):
    def __init__(self, vol_id):
        self.msg = "volume %s does not exist" % vol_id


class SnapshotDoesNotExist(AWSError):
    def __init__(self, snap_id):
        self.msg = "snapshot %s does not exist" % snap_id


class BucketAlreadyExists(AWSError):
    def __init__(self, bucket_name):
        self.msg = "bucket with name '%s' already exists on S3\n" % bucket_name
        self.msg += "(NOTE: S3's bucket namespace is shared by all AWS users)"


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
        self.msg = "No private certificate file (pem) file specified in "
        self.msg += "config (EC2_PRIVATE_KEY)"


class EC2CertDoesNotExist(AWSError):
    def __init__(self, key):
        self.msg = "EC2 certificate file %s does not exist" % key


class EC2PrivateKeyDoesNotExist(AWSError):
    def __init__(self, key):
        self.msg = "EC2 private key file %s does not exist" % key


class SpotHistoryError(AWSError):
    def __init__(self, start, end):
        self.msg = "no spot price history for the dates specified: "
        self.msg += "%s - %s" % (start, end)


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


class NoDefaultTemplateFound(ConfigError):
    def __init__(self, options=None):
        msg = "No default cluster template specified.\n\n"
        msg += "To set the default cluster template, set DEFAULT_TEMPLATE "
        msg += "in the [global] section of the config to the name of one of "
        msg += "your cluster templates"
        optlist = ', '.join(options)
        if options:
            msg += '\n\nCurrent Templates:\n\n' + optlist
        self.msg = msg
        self.options = options
        self.options_list = optlist


class ConfigNotFound(ConfigError):
    def __init__(self, *args):
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
        log.info("Config template written to %s" % self.cfg)
        log.info("Please customize the config template")

    def display_options(self):
        print 'Options:'
        print '--------'
        print '[1] Show the StarCluster config template'
        print '[2] Write config template to %s' % self.cfg
        print '[q] Quit'
        resp = raw_input('\nPlease enter your selection: ')
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


class NoClusterNodesFound(ValidationError):
    """Raised if no cluster nodes are found"""
    def __init__(self, terminated=None):
        self.msg = "No active cluster nodes found!"
        if not terminated:
            return
        self.msg += "\n\nBelow is a list of terminated instances:\n"
        for tnode in terminated:
            id = tnode.id
            reason = tnode.reason or 'N/A'
            state = tnode.state or 'N/A'
            self.msg += "\n%s (state: %s, reason: %s)" % (id, state, reason)


class NoClusterSpotRequests(ValidationError):
    """Raised if no spot requests belonging to a cluster are found"""
    def __init__(self):
        self.msg = "No cluster spot requests found!"


class MasterDoesNotExist(ClusterValidationError):
    """Raised when no master node is available"""
    def __init__(self):
        self.msg = "No master node found!"


class IncompatibleSettings(ClusterValidationError):
    """Raised when two or more settings conflict with each other"""


class InvalidProtocol(ClusterValidationError):
    """Raised when user specifies an invalid IP protocol for permission"""
    def __init__(self, protocol):
        self.msg = "protocol %s is not a valid ip protocol. options: %s"
        self.msg %= (protocol, ', '.join(static.PROTOCOLS))


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
        self.msg = ("availability_zone setting '%s' does not "
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


class ClusterNotRunning(BaseException):
    """
    Exception raised when user requests a running cluster that does not exist
    """
    def __init__(self, cluster_name):
        self.msg = "cluster %s is not running" % cluster_name


class ClusterDoesNotExist(BaseException):
    """
    Exception raised when user requests a running cluster that does not exist
    """
    def __init__(self, cluster_name):
        self.msg = "cluster '%s' does not exist" % cluster_name


class ClusterExists(BaseException):
    def __init__(self, cluster_name, is_ebs=False, stopped_ebs=False):
        ctx = dict(cluster_name=cluster_name)
        if stopped_ebs:
            self.msg = user_msgs.stopped_ebs_cluster % ctx
        elif is_ebs:
            self.msg = user_msgs.active_ebs_cluster % ctx
        else:
            self.msg = user_msgs.cluster_exists % ctx


class CancelledStartRequest(BaseException):
    def __init__(self, tag):
        self.msg = "Request to start cluster '%s' was cancelled!!!" % tag
        self.msg += "\n\nPlease be aware that instances may still be running."
        self.msg += "\nYou can check this from the output of:"
        self.msg += "\n\n   $ starcluster listclusters"
        self.msg += "\n\nIf you wish to destroy these instances please run:"
        self.msg += "\n\n   $ starcluster terminate %s" % tag
        self.msg += "\n\nYou can then use:\n\n   $ starcluster listclusters"
        self.msg += "\n\nto verify that the cluster has been terminated."
        self.msg += "\n\nIf you would like to re-use these instances, rerun"
        self.msg += "\nthe same start command with the -x (--no-create) option"


class CancelledCreateVolume(BaseException):
    def __init__(self):
        self.msg = "Request to create a new volume was cancelled!!!"
        self.msg += "\n\nPlease be aware that volume host instances"
        self.msg += " may still be running. "
        self.msg += "\n\nTo destroy these instances:"
        self.msg += "\n\n   $ starcluster terminate %s"
        self.msg += "\n\nYou can then use\n\n   $ starcluster listinstances"
        self.msg += "\n\nto verify that the volume hosts have been terminated."
        self.msg %= static.VOLUME_GROUP_NAME


class CancelledCreateImage(BaseException):
    def __init__(self, bucket, image_name):
        self.msg = "Request to create an S3 AMI was cancelled"
        self.msg += "\n\nDepending on how far along the process was before it "
        self.msg += "was cancelled, \nsome intermediate files might still be "
        self.msg += "around in /mnt on the instance."
        self.msg += "\n\nAlso, some of these intermediate files might "
        self.msg += "have been uploaded to \nS3 in the '%(bucket)s' bucket "
        self.msg += "you specified. You can check this using:"
        self.msg += "\n\n   $ starcluster showbucket %(bucket)s\n\n"
        self.msg += "Look for files like: "
        self.msg += "'%(iname)s.manifest.xml' or '%(iname)s.part.*'"
        self.msg += "\nRe-executing the same s3image command "
        self.msg += "should clean up these \nintermediate files and "
        self.msg += "also automatically override any\npartially uploaded "
        self.msg += "files in S3."
        self.msg = self.msg % {'bucket': bucket, 'iname': image_name}


CancelledS3ImageCreation = CancelledCreateImage


class CancelledEBSImageCreation(BaseException):
    def __init__(self, is_ebs_backed, image_name):
        self.msg = "Request to create EBS image %s was cancelled" % image_name
        if is_ebs_backed:
            self.msg += "\n\nDepending on how far along the process was "
            self.msg += "before it was cancelled, \na snapshot of the image "
            self.msg += "host's root volume may have been created.\nPlease "
            self.msg += "inspect the output of:\n\n"
            self.msg += "   $ starcluster listsnapshots\n\n"
            self.msg += "and clean up any unwanted snapshots"
        else:
            self.msg += "\n\nDepending on how far along the process was "
            self.msg += "before it was cancelled, \na new volume and a "
            self.msg += "snapshot of that new volume may have been created.\n"
            self.msg += "Please inspect the output of:\n\n"
            self.msg += "   $ starcluster listvolumes\n\n"
            self.msg += "   and\n\n"
            self.msg += "   $ starcluster listsnapshots\n\n"
            self.msg += "and clean up any unwanted volumes or snapshots"


class ExperimentalFeature(BaseException):
    def __init__(self, feature_name):
        self.msg = "%s is an experimental feature for this " % feature_name
        self.msg += "release. If you wish to test this feature, please set "
        self.msg += "ENABLE_EXPERIMENTAL=True in the [global] section of the"
        self.msg += " config. \n\nYou've officially been warned :D"


class ThreadPoolException(BaseException):
    def __init__(self, msg, exceptions):
        self.msg = msg
        self.exceptions = exceptions

    def print_excs(self):
        print self.format_excs()

    def format_excs(self):
        excs = []
        for exception in self.exceptions:
            e, tb_msg, jobid = exception
            excs.append('error occurred in job (id=%s): %s' % (jobid, str(e)))
            excs.append(tb_msg)
        return '\n'.join(excs)


class IncompatibleCluster(BaseException):
    main_msg = """\
The cluster '%(tag)s' was either created by a previous stable or development \
version of StarCluster or you manually created the '%(group)s' group. In any \
case '%(tag)s' cannot be used with this version of StarCluster (%(version)s).

"""

    insts_msg = """\
The cluster '%(tag)s' currently has %(num_nodes)d active nodes.

"""

    no_insts_msg = """\
The cluster '%(tag)s' does not have any nodes and is safe to terminate.

"""

    terminate_msg = """\
Please terminate the cluster using:

    $ starcluster terminate %(tag)s
"""

    def __init__(self, group):
        tag = group.name.replace(static.SECURITY_GROUP_PREFIX + '-', '')
        self.msg = "Incompatible Cluster: %(tag)s\n\n" % dict(tag=tag)
        self.msg += self.main_msg % dict(group=group.name, tag=tag,
                                         version=static.VERSION)
        states = ['pending', 'running', 'stopping', 'stopped']
        insts = filter(lambda x: x.state in states, group.instances())
        ctx = dict(tag=tag, num_nodes=len(insts))
        if insts:
            self.msg += self.insts_msg % ctx
        else:
            self.msg += self.no_insts_msg % ctx
        self.msg += self.terminate_msg % ctx
