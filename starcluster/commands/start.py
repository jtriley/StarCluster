#!/usr/bin/env python

import sys
import time

from starcluster import config
from starcluster import exception
from starcluster import optcomplete
from starcluster import static
from starcluster import cluster
from starcluster.templates import user_msgs
from starcluster.logger import log

from base import CmdBase

class CmdStart(CmdBase):
    """
    start [options] <cluster_tag>

    Start a new cluster

    Example:

        $ starcluster start mynewcluster

    This will launch a cluster named "mynewcluster" using the settings from
    the default cluster template defined in the configuration file. The
    default cluster template is specified by the 'default_template' option in
    the [global] section of the config. To use another template besides the
    default use the --cluster-template option:

        $ starcluster start --cluster-template largecluster mynewcluster

    This will do the same thing only using the settings from the "largecluster"
    cluster template defined in the config.
    """
    names = ['start']

    tag = None

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
        create = not self.opts.no_create
        cluster_exists = cluster.cluster_exists(tag, cfg)
        if cluster_exists and create:
            raise exception.ClusterExists(tag)
        if not cluster_exists and not create:
            raise exception.ClusterDoesNotExist(tag)
        scluster = cfg.get_cluster_template(template, tag)
        scluster.update(self.specified_options_dict)
        validate_running = self.opts.no_create
        validate_only = self.opts.validate_only
        try:
            scluster._validate(validate_running=validate_running)
            if validate_only:
                return
        except exception.ClusterValidationError,e:
            log.error('settings for cluster template "%s" are not valid:' % template)
            raise
        if self.opts.spot_bid is not None:
            cmd = ' '.join(sys.argv[1:]) + ' --no-create'
            launch_group = static.SECURITY_GROUP_TEMPLATE % tag
            msg = user_msgs.spotmsg % {'cmd':cmd,
                                       'launch_group': launch_group}
            self.warn_experimental(msg)
        self.catch_ctrl_c()
        scluster.start(create=create, validate=False)
        if self.opts.login_master:
            cluster.ssh_to_master(tag, self.cfg)

