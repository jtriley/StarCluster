#!/usr/bin/env python
"""
starcluster [global-opts] action [action-opts] [<action-args> ...]
"""

__description__ = """
StarCluster - (http://web.mit.edu/starcluster)
Software Tools for Academics and Researchers (STAR)
Please submit bug reports to starcluster@mit.edu
"""

__moredoc__ = """
Each command consists of a class, which has the following properties:

- Must have a class member 'names' which is a list of the names for the command;

- Can optionally have a addopts(self, parser) method which adds options to the
  given parser. This defines command options.
"""

from starcluster import __version__
__author__ = "Justin Riley <justin.t.riley@gmail.com>"

import os
import sys
import time
import socket
import signal
from datetime import datetime, timedelta
from pprint import pprint, pformat

# hack for now to ignore pycrypto 2.0.1 using md5 and sha
# why is pycrypto 2.1.0 not on pypi?
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from boto.exception import EC2ResponseError, S3ResponseError
from starcluster import cluster
from starcluster import node
from starcluster import config
from starcluster import exception
from starcluster import static
from starcluster import optcomplete
from starcluster import image
from starcluster import volume
from starcluster import utils
from starcluster.templates import experimental
from starcluster.logger import log, console, DEBUG

#try:
    #import optcomplete
    #CmdComplete = optcomplete.CmdComplete
#except ImportError,e:
    #optcomplete, CmdComplete = None, object

class CmdBase(optcomplete.CmdComplete):
    parser = None
    opts = None
    gopts = None

    @property
    def goptions_dict(self):
        return dict(self.gopts.__dict__)

    @property
    def options_dict(self):
        return dict(self.opts.__dict__)

    @property
    def specified_options_dict(self):
        """ only return options with non-None value """
        specified = {}
        options = self.options_dict
        for opt in options:
            if options[opt] is not None:
                specified[opt] = options[opt]
        return specified

    @property
    def cfg(self):
        return self.goptions_dict.get('CONFIG')

    def cancel_command(self, signum, frame):
        print
        log.info("Exiting...")
        sys.exit(1)

    def catch_ctrl_c(self, handler=None):
        handler = handler or self.cancel_command
        signal.signal(signal.SIGINT, handler)

    def warn_experimental(self, msg):
        for l in msg.splitlines():
            log.warn(l)
        num_secs = 10
        r = range(1,num_secs+1)
        r.reverse()
        print
        log.warn("Waiting %d seconds before continuing..." % num_secs)
        log.warn("Press CTRL-C to cancel...")
        for i in r:
            sys.stdout.write('%d...' % i)
            sys.stdout.flush()
            time.sleep(1)
        print

class CmdStart(CmdBase):
    """
    start [options] <cluster_tag>

    Start a new cluster 

    Example: 

        $ starcluster start mynewcluster

    This will launch a cluster tagged "mynewcluster" using the
    settings from the "default" cluster template defined
    in the configuration file. The default cluster template
    is the template that has DEFAULT=True in the configuration file.

        $ starcluster start --cluster largecluster mynewcluster

    This will do the same thing only using the "largecluster" 
    cluster template rather than the "default" template assuming 
    "largecluster" has been defined in the configuration file.
    """
    names = ['start']

    tag = None

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig()
                cfg.load()
                return optcomplete.ListCompleter(cfg.get_cluster_names())
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def addopts(self, parser):
        opt = parser.add_option("-x","--no-create", dest="no_create",
            action="store_true", default=False, help="Do not launch new ec2 " + \
"instances when starting cluster (uses existing instances instead)")
        opt = parser.add_option("-v","--validate-only", dest="validate_only",
            action="store_true", default=False, help="Only validate cluster " + \
"settings, do not start a cluster")
        parser.add_option("-l","--login-master", dest="login_master",
            action="store_true", default=False, 
            help="ssh to ec2 cluster master node after launch")
        opt = parser.add_option("-b","--bid", dest="spot_bid",
            action="store", type="float", default=None, 
            help="Requests spot instances instead of the usual flat rate " + \
                 "instances. Uses SPOT_BID as max bid for the request. " + \
                 "(EXPERIMENTAL)")
        parser.add_option("-c","--cluster-template", dest="cluster_template",
            action="store", type="string", default=None, 
            help="cluster template to use from the config file")
        parser.add_option("-d","--description", dest="cluster_description",
            action="store", type="string", 
            default="Cluster requested at %s" % time.strftime("%Y%m%d%H%M"), 
            help="brief description of cluster")
        parser.add_option("-s","--cluster-size", dest="cluster_size",
            action="store", type="int", default=None, 
            help="number of ec2 instances to launch")
        parser.add_option("-u","--cluster-user", dest="cluster_user",
            action="store", type="string", default=None, 
            help="name of user to create on cluster (defaults to sgeadmin)")
        opt = parser.add_option("-S","--cluster-shell", dest="cluster_shell",
            action="store", choices=static.AVAILABLE_SHELLS.keys(),
            default=None, help="shell for cluster user (defaults to bash)")
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(opt.choices)
        parser.add_option("-m","--master-image-id", dest="master_image_id",
            action="store", type="string", default=None, 
            help="AMI to use when launching master")
        parser.add_option("-n","--node-image-id", dest="node_image_id",
            action="store", type="string", default=None, 
            help="AMI to use when launching nodes")
        opt = parser.add_option("-I","--master-instance-type", dest="master_instance_type",
            action="store", choices=static.INSTANCE_TYPES.keys(),
            default=None, help="specify machine type for the master instance")
        opt = parser.add_option("-i","--node-instance-type", dest="node_instance_type",
            action="store", choices=static.INSTANCE_TYPES.keys(),
            default=None, help="specify machine type for the node instances")
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(opt.choices)
        parser.add_option("-a","--availability-zone", dest="availability_zone",
            action="store", type="string", default=None, 
            help="availability zone to launch ec2 instances in")
        parser.add_option("-k","--keyname", dest="keyname",
            action="store", type="string", default=None, 
            help="name of the AWS keypair to use when launching the cluster")
        parser.add_option("-K","--key-location", dest="key_location",
            action="store", type="string", default=None, metavar="FILE",
            help="path to ssh private key used for this cluster")

    def cancel_command(self, signum, frame):
        raise exception.CancelledStartRequest(self.tag)

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a <tag_name> for this cluster")
        cfg = self.cfg
        use_experimental = cfg.globals.get('enable_experimental')
        if self.opts.spot_bid is not None and not use_experimental:
            raise exception.ExperimentalFeature('Using spot instances')
        tag = self.tag = args[0]
        template = self.opts.cluster_template
        if not template:
            template = cfg.get_default_cluster_template(tag)
            log.info("Using default cluster template: %s" % template)
        scluster = cfg.get_cluster_template(template, tag)
        scluster.update(self.specified_options_dict)
        if cluster.cluster_exists(tag,cfg) and not self.opts.no_create:
            raise exception.ClusterExists(tag)
        #from starcluster.utils import ipy_shell; ipy_shell();
        check_running = self.opts.no_create
        if check_running:
            log.info("Validating existing instances...")
            if scluster.is_running_valid():
                log.info('Existing instances are valid')
            else:
                log.error('existing instances are not compatible with cluster' + \
                          ' template settings')
                sys.exit(1)
        log.info("Validating cluster template settings...")
        if scluster.is_valid():
            log.info('Cluster template settings are valid')
            if not self.opts.validate_only:
                if self.opts.spot_bid is not None:
                    cmd = ' '.join(sys.argv[1:]) + ' --no-create'
                    launch_group = static.SECURITY_GROUP_TEMPLATE % tag
                    msg = experimental.spotmsg % {'cmd':cmd, 
                                                  'launch_group': launch_group}
                    self.warn_experimental(msg)
                self.catch_ctrl_c()
                scluster.start(create=not self.opts.no_create)
                if self.opts.login_master:
                    cluster.ssh_to_master(tag, self.cfg)
        else:
            log.error('settings for cluster template "%s" are not valid' % template)
            sys.exit(1)

class CmdStop(CmdBase):
    """
    stop [options] <cluster>

    Shutdown a running cluster

    Example:

        $ starcluster stop mycluster

    This will stop a currently running cluster tagged "mycluster"
    """
    names = ['stop']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig()
                cfg.load()
                clusters = cluster.get_cluster_security_groups(cfg)
                completion_list = [sg.name.replace(static.SECURITY_GROUP_PREFIX+'-','') for sg in clusters]
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)
                
    def addopts(self, parser):
        opt = parser.add_option("-c","--confirm", dest="confirm", 
                                action="store_true", default=False, 
                                help="Do not prompt for confirmation, " + \
                                "just shutdown the cluster")

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        cfg = self.cfg
        for cluster_name in args:
            cl = cluster.get_cluster(cluster_name,cfg)
            if not self.opts.confirm:
                resp = raw_input("Shutdown cluster %s (y/n)? " % cluster_name)
                if resp not in ['y','Y', 'yes']:
                    log.info("Aborting...")
                    continue
            cluster.stop_cluster(cluster_name, cfg)

class CmdSshMaster(CmdBase):
    """
    sshmaster [options] <cluster>

    SSH to a cluster's master node

    Example:

        $ sshmaster mycluster
    """
    names = ['sshmaster']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig()
                cfg.load()
                clusters = cluster.get_cluster_security_groups(cfg)
                completion_list = [sg.name.replace(static.SECURITY_GROUP_PREFIX+'-','') for sg in clusters]
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def addopts(self, parser):
        opt = parser.add_option("-u","--user", dest="USER", action="store", 
                                type="string", default='root', 
                                help="login as USER (defaults to root)")

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        for arg in args:
            cluster.ssh_to_master(arg, self.cfg, user=self.opts.USER)

class CmdSshNode(CmdBase):
    """
    sshnode <cluster> <node>

    SSH to a cluster node

    Examples:

        $ starcluster sshnode mycluster master
        $ starcluster sshnode mycluster node001
        ...

    or same thing in shorthand:

        $ starcluster sshnode mycluster 0
        $ starcluster sshnode mycluster 1
        ...
    """
    names = ['sshnode']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig()
                cfg.load()
                clusters = cluster.get_cluster_security_groups(cfg)
                completion_list = [sg.name.replace(static.SECURITY_GROUP_PREFIX+'-','') for sg in clusters]
                max_num_nodes = 0
                for scluster in clusters:
                    num_instances = len(scluster.instances())
                    if num_instances > max_num_nodes:
                        max_num_nodes = num_instances
                completion_list.extend(['master'])
                completion_list.extend([str(i) for i in range(0,num_instances)])
                completion_list.extend(["node%03d" % i for i in range(1,num_instances)])
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                print e
                log.error('something went wrong fix me: %s' % e)

    def addopts(self, parser):
        opt = parser.add_option("-u","--user", dest="USER", action="store",
                                type="string", default='root', 
                                help="login as USER (defaults to root)")

    def execute(self, args):
        if len(args) != 2:
            self.parser.error("please specify a <cluster> and <node> to connect to")
        scluster = args[0]
        ids = args[1:]
        for id in ids:
            cluster.ssh_to_cluster_node(scluster, id, self.cfg,
                                        user=self.opts.USER)

class CmdSshInstance(CmdBase):
    """
    sshintance [options] <instance-id>

    SSH to an EC2 instance

    Examples:

        $ starcluster sshinstance i-14e9157c
        $ starcluster sshinstance ec2-123-123-123-12.compute-1.amazonaws.com 
    
    """
    names = ['sshinstance']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig()
                cfg.load()
                ec2 = cfg.get_easy_ec2()
                instances = ec2.get_all_instances()
                completion_list = [i.id for i in instances]
                completion_list.extend([i.dns_name for i in instances])
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def addopts(self, parser):
        opt = parser.add_option("-u","--user", dest="USER", action="store", 
                                type="string", default='root', 
                                help="login as USER (defaults to root)")

    def execute(self, args):
        if not args:
            self.parser.error(
                "please specify an instance id or dns name to connect to")
        for arg in args:
            # user specified dns name or instance id
            instance = args[0]
            node.ssh_to_node(instance, self.cfg, user=self.opts.USER)

class CmdListClusters(CmdBase):
    """
    listclusters 

    List all active clusters
    """
    names = ['listclusters']
    def execute(self, args):
        cfg = self.cfg
        cluster.list_clusters(cfg)

class CmdCreateImage(CmdBase):
    """
    createimage [options] <instance-id> <image_name> <bucket> 

    Create a new image (AMI) from a currently running EC2 instance

    Example:

        $ starcluster createimage i-999999 my-new-image mybucket

    NOTE: It is recommended not to create a new StarCluster AMI from
    an instance launched by StarCluster. Rather, launch a single 
    StarCluster instance using ElasticFox or the EC2 API tools, modify
    it to your liking, and then use this command to create a new AMI from 
    the running instance.
    """
    names = ['createimage']

    bucket = None
    image_name = None

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig()
                cfg.load()
                ec2 = cfg.get_easy_ec2()
                instances = ec2.get_all_instances()
                completion_list = [i.id for i in instances]
                completion_list.extend([i.dns_name for i in instances])
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def addopts(self, parser):
        opt = parser.add_option(
            "-c","--confirm", dest="confirm",
            action="store_true", default=False, 
            help="Do not warn about re-imaging StarCluster instances")
        opt = parser.add_option(
            "-r","--remove-image-files", dest="remove_image_files",
            action="store_true", default=False, 
            help="Remove generated image files on the instance after registering")
        opt = parser.add_option(
            "-d","--description", dest="description", action="store", 
            type="string", default=time.strftime("%Y%m%d%H%M"), 
            help="short description of this AMI")
        opt = parser.add_option(
            "-k","--kernel-id", dest="kernel_id", action="store", 
            type="string", default=None,
            help="kernel id for the new AMI")
        opt = parser.add_option(
            "-R","--ramdisk-id", dest="ramdisk_id", action="store", 
            type="string", default=None,
            help="ramdisk id for the new AMI")

    def cancel_command(self, signum, frame):
        raise exception.CancelledCreateImage(self.bucket, self.image_name)

    def execute(self, args):
        if len(args) != 3:
            self.parser.error('you must specify an instance-id, image name, and bucket')
        instanceid, image_name, bucket = args
        self.bucket = bucket
        self.image_name = image_name
        cfg = self.cfg
        ec2 = cfg.get_easy_ec2()
        i = ec2.get_instance(instanceid)
        if not self.opts.confirm:
            for group in i.groups:
                if group.id.startswith(static.SECURITY_GROUP_PREFIX):
                    log.warn("Instance %s is a StarCluster instance" % i.id)
                    print
                    log.warn("Creating an image from a StarCluster instance " + \
                    "can lead to problems when attempting to use the resulting " + \
                    "image with StarCluster later on")
                    print
                    log.warn(
                    "The recommended way to re-image a StarCluster AMI is " + \
                    "to launch a single instance using either ElasticFox, the " +\
                    "EC2 command line tools, or the AWS management console. " +\
                    "Then login to the instance, modify it, and use this " + \
                    "command to create a new AMI from it.")
                    print
                    resp = raw_input("Continue anyway (y/n)? ")
                    if resp not in ['y','Y','yes']:
                        log.info("Aborting...")
                        sys.exit(1)
                    break
        self.catch_ctrl_c()
        ami_id = image.create_image(instanceid, image_name, bucket, cfg,
                           **self.specified_options_dict)
        log.info("Your new AMI id is: %s" % ami_id)

class CmdCreateVolume(CmdBase):
    """
    createvolume [options] <volume_size> <volume_zone>

    Create a new EBS volume for use with StarCluster
    """

    names = ['createvolume']

    def addopts(self, parser):
        opt = parser.add_option(
            "-i","--image-id", dest="image_id",
            action="store", type="string", default=None,
            help="Specifies the AMI to use when launching volume host instance")
        opt = parser.add_option(
            "-n","--no-shutdown", dest="shutdown_instance",
            action="store_false", default=True,
            help="Do not shutdown volume host instance after creating volume")
        #opt = parser.add_option(
            #"-a","--add-to-config", dest="add_to_cfg",
            #action="store_true", default=False,
            #help="Add a new volume section to the config after creating volume")
    
    def cancel_command(self, signum, frame):
        raise exception.CancelledCreateVolume()
    
    def execute(self, args):
        if len(args) != 2:
            self.parser.error("you must specify a size (in GB) and an availability zone")
        size, zone = args
        vc = volume.VolumeCreator(self.cfg, **self.specified_options_dict)
        self.catch_ctrl_c()
        volid = vc.create(size, zone)
        if volid:
            log.info("Your new %sGB volume %s has been created successfully" % \
                     (size,volid))
        else:
            log.error("failed to create new volume")

class CmdListZones(CmdBase):
    """
    listzones

    List all EC2 availability zones
    """
    names = ['listzones']
    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        ec2.list_zones()

class CmdListImages(CmdBase):
    """
    listimages [options]

    List all registered EC2 images (AMIs)
    """
    names = ['listimages']

    def addopts(self, parser):
        opt = parser.add_option(
            "-x","--executable-by-me", dest="executable",
            action="store_true", default=False,
            help="Show images that you have permission to execute")

    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        if self.opts.executable:
            ec2.list_executable_images()
        else:
            ec2.list_registered_images()

class CmdListBuckets(CmdBase):
    """
    listbuckets

    List all S3 buckets
    """
    names = ['listbuckets']
    def execute(self, args):
        s3 = self.cfg.get_easy_s3()
        buckets = s3.list_buckets()

class CmdShowImage(CmdBase):
    """
    showimage <image_id>

    Show all AMI parts and manifest files on S3 for an EC2 image (AMI)

    Example:

        $ starcluster showimage ami-999999
    """
    names = ['showimage']
    def execute(self, args):
        if not args:
            self.parser.error('please specify an AMI id')
        ec2 = self.cfg.get_easy_ec2()
        for arg in args:
            ec2.list_image_files(arg)
   
class CmdShowBucket(CmdBase):
    """
    showbucket <bucket>

    Show all files in an S3 bucket

    Example:

        $ starcluster showbucket mybucket
    """
    names = ['showbucket']
    def execute(self, args):
        if not args:
            self.parser.error('please specify an S3 bucket')
        for arg in args:
            s3 = self.cfg.get_easy_s3()
            bucket = s3.list_bucket(arg)

class CmdRemoveVolume(CmdBase):
    """
    removevolume [options] <volume_id> 

    Delete one or more EBS volumes

    WARNING: This command *permanently* removes an EBS volume.
    Be careful!

    Example:

        $ starcluster removevolume vol-999999
    """
    names = ['removevolume']

    def addopts(self, parser):
        parser.add_option("-c","--confirm", dest="confirm", action="store_true",
            default=False,
            help="do not prompt for confirmation, just remove the volume")

    def execute(self, args):
        if not args:
            self.parser.error("no volumes specified. exiting...")
        for arg in args:
            volid = arg
            ec2 = self.cfg.get_easy_ec2()
            vol = ec2.get_volume(volid)
            if vol.status in ['attaching', 'in-use']:
                log.error("volume is currently in use. aborting...")
                return
            if vol.status == 'detaching':
                log.error("volume is currently detaching. " + \
                          "please wait a few moments and try again...")
                return
            if not self.opts.confirm:
                resp = raw_input("**PERMANENTLY** delete %s (y/n)? " % volid)
                if resp not in ['y','Y', 'yes']:
                    log.info("Aborting...")
                    return
            if vol.delete():
                log.info("Volume %s deleted successfully" % vol.id)
            else:
                log.error("Error deleting volume %s" % vol.id)

class CmdRemoveImage(CmdBase):
    """
    removeami [options] <imageid> 

    Deregister an EC2 image (AMI) and remove it from S3

    WARNING: This command *permanently* removes an AMI from 
    EC2/S3 including all AMI parts and manifest. Be careful!

    Example:

        $ starcluster removeami ami-999999
    """
    names = ['removeimage']

    def addopts(self, parser):
        parser.add_option("-p","--pretend", dest="pretend", action="store_true",
            default=False,
            help="pretend run, dont actually remove anything")
        parser.add_option("-c","--confirm", dest="confirm", action="store_true",
            default=False,
            help="do not prompt for confirmation, just remove the image")

    def execute(self, args):
        if not args:
            self.parser.error("no images specified. exiting...")
        for arg in args:
            imageid = arg
            ec2 = self.cfg.get_easy_ec2()
            image = ec2.get_image(imageid)
            confirmed = self.opts.confirm
            pretend = self.opts.pretend
            if not confirmed:
                if not pretend:
                    resp = raw_input("**PERMANENTLY** delete %s (y/n)? " % imageid)
                    if resp not in ['y','Y', 'yes']:
                        log.info("Aborting...")
                        return
            ec2.remove_image(imageid, pretend=pretend)

class CmdListInstances(CmdBase):
    """
    listinstances [options]

    List all running EC2 instances
    """
    names = ['listinstances']

    def addopts(self, parser):
        parser.add_option("-t","--show-terminated", dest="show_terminated", action="store_true",
            default=False,
            help="show terminated instances") 

    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        ec2.list_all_instances(self.opts.show_terminated)

class CmdListSpots(CmdBase):
    """
    listspots

    List all EC2 spot instance requests
    """
    names = ['listspots']
    def addopts(self, parser):
        parser.add_option("-c", "--show-closed", dest="show_closed",
                          action="store_true", default=False, 
                          help="show closed spot instance requests")
    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        ec2.list_all_spot_instances(self.opts.show_closed)

class CmdShowConsole(CmdBase):
    """
    showconsole <instance-id>

    Show console output for an EC2 instance

    Example:

        $ starcluster showconsole i-999999

    This will display the startup logs for instance i-999999
    """
    names = ['showconsole']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig()
                cfg.load()
                ec2 = cfg.get_easy_ec2()
                instances = ec2.get_all_instances()
                completion_list = [i.id for i in instances]
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                log.error('something went wrong fix me: %s' % e)

    def execute(self, args):
        if not len(args) == 1:
            self.parser.error('please provide an instance id')
        ec2 = self.cfg.get_easy_ec2()
        ec2.show_console_output(args[0])

class CmdListVolumes(CmdBase):
    """
    listvolumes

    List all EBS volumes
    """
    names = ['listvolumes']
    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        ec2.list_volumes()

class CmdListPublic(CmdBase):
    """
    listpublic

    List all public StarCluster images on EC2
    """
    names = ['listpublic']
    def execute(self, args):
        ec2 = self.cfg.get_easy_ec2()
        ec2.list_starcluster_public_images()

class CmdRunPlugin(CmdBase):
    """
    runplugin <plugin_name> <cluster_tag>

    Run a StarCluster plugin on a runnning cluster

    plugin_name - name of plugin section defined in the config
    cluster_tag - tag name of a running StarCluster

    Example: 

       $ starcluster runplugin myplugin mycluster
    """
    names = ['runplugin']
    def execute(self,args):
        if len(args) != 2:
            self.parser.error("Please provide a plugin_name and <cluster_tag>")
        plugin_name, cluster_tag = args
        cluster.run_plugin(plugin_name, cluster_tag, self.cfg)

class CmdSpotHistory(CmdBase):
    """
    spothistory [options] <instance_type>

    Show spot instance pricing history stats (last 30 days by default)

    Examples:

    To show the current, max, and average spot price for m1.small instance type:

        $ starcluster spothistory m1.small

    Do the same thing but also plot the spot history over time using matplotlib:

        $ starcluster spothistory -p m1.small
    """
    names = ['spothistory']

    def addopts(self, parser):
        now_tup = datetime.now()
        now = utils.datetime_tuple_to_iso(now_tup)
        thirty_days_ago = utils.datetime_tuple_to_iso(now_tup - timedelta(days=30))
        parser.add_option("-d","--days", dest="days_ago",
            action="store", type="float", 
            help="provide history in the last DAYS_AGO days " + \
                          "(overrides -s and -e options)") 
        parser.add_option("-s","--start-time", dest="start_time",
            action="store", type="string", 
            default=thirty_days_ago, 
            help="show price history after START_TIME" + \
                          "(e.g. 2010-01-15T22:22:22)")
        parser.add_option("-e","--end-time", dest="end_time",
            action="store", type="string", 
            default=now, 
            help="show price history up until END_TIME" + \
                          "(e.g. 2010-02-15T22:22:22)")
        parser.add_option("-p","--plot", dest="plot",
            action="store_true",  default=False,
            help="plot spot history using matplotlib")

    def execute(self,args):
        instance_types = ', '.join(static.INSTANCE_TYPES.keys())
        if len(args) != 1:
            self.parser.error('please provide an instance type (options: %s)' % \
                             instance_types)
        instance_type = args[0]
        if not static.INSTANCE_TYPES.has_key(instance_type):
            self.parser.error('invalid instance type. possible options: %s' % \
                              instance_types)
        start = self.opts.start_time
        end = self.opts.end_time
        if self.opts.days_ago:
            now =  datetime.now()
            end = utils.datetime_tuple_to_iso(now)
            start = utils.datetime_tuple_to_iso(
                now - timedelta(days=self.opts.days_ago))
        ec2 = self.cfg.get_easy_ec2()
        ec2.get_spot_history(instance_type, start, end, self.opts.plot)

class CmdShell(CmdBase):
    """
    shell

    Load interactive IPython shell for starcluster development
    
    The following objects are automatically available at the prompt:

        cfg - starcluster.config.StarClusterConfig instance
        ec2 - starcluster.awsutils.EasyEC2 instance
        s3 - starcluster.awsutils.EasyS3 instance

    All starcluster modules are automatically imported in the IPython session
    """
    names = ['shell']
    def execute(self,args):
        cfg = self.cfg
        ec2 = cfg.get_easy_ec2()
        s3 = ec2.s3
        import starcluster
        for modname in starcluster.__all__:
            log.info('Importing module %s' % modname)
            fullname = starcluster.__name__ + '.' + modname
            try:
                __import__(fullname)
                locals()[modname] = sys.modules[fullname]
            except ImportError,e:
                log.error("Error loading module %s: %s" % (modname, e))
        from starcluster.utils import ipy_shell; ipy_shell();

class CmdHelp:
    """
    help

    Show StarCluster usage
    """
    names =['help']
    def execute(self, args):
        import optparse
        if args:
            cmdname = args[0]
            try:
                sc = subcmds_map[cmdname]
                lparser = optparse.OptionParser(sc.__doc__.strip())
                if hasattr(sc, 'addopts'):
                    sc.addopts(lparser)
                lparser.print_help()
            except KeyError:
                raise SystemExit("Error: invalid command '%s'" % cmdname)
        else:
            gparser.parse_args(['--help'])

def get_description():
    return __description__.replace('\n','',1)

def parse_subcommands(gparser, subcmds):

    """Parse given global arguments, find subcommand from given list of
    subcommand objects, parse local arguments and return a tuple of global
    options, selected command object, command options, and command arguments.
    Call execute() on the command object to run. The command object has members
    'gopts' and 'opts' set for global and command options respectively, you
    don't need to call execute with those but you could if you wanted to."""

    import optparse
    global subcmds_map # needed for help command only.

    print get_description()

    # Build map of name -> command and docstring.
    subcmds_map = {}
    gparser.usage += '\n\nAvailable Actions\n'
    for sc in subcmds:
        helptxt = sc.__doc__.splitlines()[3].strip()
        gparser.usage += '- %s: %s\n' % (', '.join(sc.names),
                                       helptxt)
        for n in sc.names:
            assert n not in subcmds_map
            subcmds_map[n] = sc

    # Declare and parse global options.
    gparser.disable_interspersed_args()

    gopts, args = gparser.parse_args()
    if not args:
        gparser.print_help()
        raise SystemExit("\nError: you must specify an action.")
    subcmdname, subargs = args[0], args[1:]

    # set debug level if specified
    if gopts.DEBUG:
        console.setLevel(DEBUG)
    # load StarClusterConfig into global options
    try:
        cfg = config.StarClusterConfig(gopts.CONFIG)
        cfg.load()
    except exception.ConfigNotFound,e:
        log.error(e.msg)
        e.display_options()
        sys.exit(1)
    except exception.ConfigError,e:
        log.error(e.msg)
        sys.exit(1)
    gopts.CONFIG = cfg

    # Parse command arguments and invoke command.
    try:
        sc = subcmds_map[subcmdname]
        lparser = optparse.OptionParser(sc.__doc__.strip())
        if hasattr(sc, 'addopts'):
            sc.addopts(lparser)
        sc.parser = lparser
        sc.gopts = gopts
        sc.opts, subsubargs = lparser.parse_args(subargs)
    except KeyError:
        raise SystemExit("Error: invalid command '%s'" % subcmdname)

    return gopts, sc, sc.opts, subsubargs

def main():
    # Create global options parser.
    global gparser # only need for 'help' command (optional)
    import optparse
    gparser = optparse.OptionParser(__doc__.strip(), version=__version__)
    gparser.add_option("-d","--debug", dest="DEBUG", action="store_true",
        default=False,
        help="print debug messages (useful for diagnosing problems)")
    gparser.add_option("-c","--config", dest="CONFIG", action="store",
        metavar="FILE",
        help="use alternate config file (default: %s)" % \
                       static.STARCLUSTER_CFG_FILE)

    # Declare subcommands.
    subcmds = [
        CmdStart(),
        CmdStop(),
        CmdListClusters(),
        CmdSshMaster(),
        CmdSshNode(),
        CmdSshInstance(),
        CmdListInstances(),
        CmdListImages(),
        CmdListPublic(),
        CmdCreateImage(),
        CmdRemoveImage(),
        CmdListVolumes(),
        CmdCreateVolume(),
        CmdRemoveVolume(),
        CmdListSpots(),
        CmdSpotHistory(),
        CmdShowConsole(),
        CmdListZones(),
        CmdListBuckets(),
        CmdShowBucket(),
        CmdShowImage(),
        CmdShell(),
        CmdHelp(),
    ]

    # subcommand completions
    scmap = {}
    for sc in subcmds:
        for n in sc.names:
            scmap[n] = sc
  
    if optcomplete:
        listcter = optcomplete.ListCompleter(scmap.keys())
        subcter = optcomplete.NoneCompleter()
        optcomplete.autocomplete(
            gparser, listcter, None, subcter, subcommands=scmap)
    elif 'COMP_LINE' in os.environ:
        return -1

    gopts, sc, opts, args = parse_subcommands(gparser, subcmds)
    if args and args[0] =='help':
        sc.parser.print_help()
        sys.exit(0)
    try:
        sc.execute(args)
    except exception.BaseException,e:
        lines = e.msg.splitlines()
        for l in lines:
            log.error(l)
        #log.error(e.msg)
        sys.exit(1)
    except EC2ResponseError,e:
        log.error("%s: %s" % (e.error_code, e.error_message))
        sys.exit(1)
    except S3ResponseError,e:
        log.error("%s: %s" % (e.error_code, e.error_message))
        sys.exit(1)
    except socket.gaierror,e:
        log.error("Unable to connect: %s" % e)
        log.error("Check your internet connection?")
        sys.exit(1)
    except Exception,e:
        import traceback
        if not gopts.DEBUG:
            traceback.print_exc()
        log.debug(traceback.format_exc())
        print
        log.error("Oops! Looks like you've found a bug in StarCluster")
        log.error("Debug file written to: %s" % static.DEBUG_FILE)
        log.error("Please submit this file, minus any private information,")
        log.error("to starcluster@mit.edu")
        sys.exit(1)

def test():
    pass

if os.environ.has_key('starcluster_commands_test'):
    test()
elif __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print "Interrupted, exiting."
