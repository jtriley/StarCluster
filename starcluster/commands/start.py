#!/usr/bin/env python

import sys
import time

from starcluster import config
from starcluster import static
from starcluster import exception
from starcluster import optcomplete
from starcluster.templates import user_msgs
from starcluster.logger import log

from completers import ClusterCompleter


class CmdStart(ClusterCompleter):
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
        cfg = config.StarClusterConfig().load()
        templates = cfg.get_cluster_names().keys()
        opt = parser.add_option("-c", "--cluster-template", action="store",
                                dest="cluster_template", choices=templates,
                                default=None,
                                help="cluster template to use " + \
                                "from the config file")
        parser.add_option("-x", "--no-create", dest="no_create",
                          action="store_true", default=False,
                          help="Do not launch new EC2 instances when " + \
                          "starting cluster (use existing instances instead)")
        parser.add_option("-o", "--create-only", dest="create_only",
                          action="store_true", default=False,
                          help="Only launch/start EC2 instances, " + \
                          "do not perform any setup routines")
        parser.add_option("-v", "--validate-only", dest="validate_only",
                          action="store_true", default=False,
                          help="Only validate cluster settings, do " + \
                          "not start a cluster")
        parser.add_option("-V", "--skip-validation", dest="validate",
                          action="store_false", default=True,
                          help="Do not validate cluster settings")
        parser.add_option("-l", "--login-master", dest="login_master",
                          action="store_true", default=False,
                          help="ssh to ec2 cluster master node after launch")
        parser.add_option("-q", "--disable-queue", dest="disable_queue",
                          action="store_true", default=None,
                          help="Do not configure a queueing system (SGE)")
        parser.add_option("-r", "--refresh-interval", dest="refresh_interval",
                          type="int", action="callback", default=None,
                          callback=self._positive_int,
                          help="Refresh interval when waiting for cluster " + \
                          "nodes to come up (default: 30)")
        parser.add_option("-b", "--bid", dest="spot_bid", action="store",
                          type="float", default=None,
                          help="Requests spot instances instead of flat " + \
                          "rate instances. Uses SPOT_BID as max bid for " + \
                          "the request.")
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(opt.choices)
        parser.add_option("-d", "--description", dest="cluster_description",
                          action="store", type="string",
                          default="Cluster requested at %s" % \
                          time.strftime("%Y%m%d%H%M"),
                          help="brief description of cluster")
        parser.add_option("-s", "--cluster-size", dest="cluster_size",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="number of ec2 instances to launch")
        parser.add_option("-u", "--cluster-user", dest="cluster_user",
                          action="store", type="string", default=None,
                          help="name of user to create on cluster " + \
                          "(defaults to sgeadmin)")
        opt = parser.add_option("-S", "--cluster-shell", dest="cluster_shell",
                                action="store",
                                choices=static.AVAILABLE_SHELLS.keys(),
                                default=None,
                                help="shell for cluster user " + \
                                "(defaults to bash)")
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(opt.choices)
        parser.add_option("-m", "--master-image-id", dest="master_image_id",
                          action="store", type="string", default=None,
                          help="AMI to use when launching master")
        parser.add_option("-n", "--node-image-id", dest="node_image_id",
                          action="store", type="string", default=None,
                          help="AMI to use when launching nodes")
        parser.add_option("-I", "--master-instance-type",
                          dest="master_instance_type", action="store",
                          choices=static.INSTANCE_TYPES.keys(), default=None,
                          help="specify machine type for the master instance")
        opt = parser.add_option("-i", "--node-instance-type",
                                dest="node_instance_type", action="store",
                                choices=static.INSTANCE_TYPES.keys(),
                                default=None,
                                help="specify machine type for the node " + \
                                "instances")
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(opt.choices)
        parser.add_option("-a", "--availability-zone",
                          dest="availability_zone", action="store",
                          type="string", default=None,
                          help="availability zone to launch ec2 instances in")
        parser.add_option("-k", "--keyname", dest="keyname", action="store",
                          type="string", default=None,
                          help="name of the AWS keypair to use when " + \
                          "launching the cluster")
        parser.add_option("-K", "--key-location", dest="key_location",
                          action="store", type="string", default=None,
                          metavar="FILE",
                          help="path to ssh private key used for this cluster")

    def cancel_command(self, signum, frame):
        raise exception.CancelledStartRequest(self.tag)

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = self.tag = args[0]
        create = not self.opts.no_create
        create_only = self.opts.create_only
        cluster_exists = self.cm.get_cluster_or_none(tag)
        validate = self.opts.validate
        validate_running = self.opts.no_create
        validate_only = self.opts.validate_only
        if cluster_exists and create:
            stopped_ebs = cluster_exists.is_cluster_stopped()
            is_ebs = False
            if not stopped_ebs:
                is_ebs = cluster_exists.is_ebs_cluster()
            raise exception.ClusterExists(tag, is_ebs=is_ebs,
                                          stopped_ebs=stopped_ebs)
        if not cluster_exists and not create:
            raise exception.ClusterDoesNotExist(tag)
        scluster = None
        if cluster_exists:
            validate_running = True
            scluster = self.cm.get_cluster(tag)
            log.info(
                "Using original template used to launch cluster '%s'" % \
                scluster.cluster_tag)
        else:
            template = self.opts.cluster_template
            if not template:
                template = self.cm.get_default_cluster_template()
                log.info("Using default cluster template: %s" % template)
            scluster = self.cm.get_cluster_template(template, tag)
        scluster.update(self.specified_options_dict)
        if not self.opts.refresh_interval:
            interval = self.cfg.globals.get("refresh_interval")
            scluster.refresh_interval = interval
        if validate:
            try:
                scluster._validate(validate_running=validate_running)
            except exception.ClusterValidationError:
                if not cluster_exists:
                    log.error(
                        'settings for cluster template "%s" are not valid:' % \
                        template)
                raise
        else:
            log.warn("SKIPPING VALIDATION - USE AT YOUR OWN RISK")
        if validate_only:
            return
        if self.opts.spot_bid is not None:
            cmd = ' '.join(sys.argv[1:])
            cmd = cmd.replace('--no-create', '').replace('-x', '')
            cmd += ' --no-create'
            msg = user_msgs.spotmsg % {'cmd': cmd,
                                       'size': scluster.cluster_size,
                                       'tag': tag}
            self.warn_experimental(msg, num_secs=5)
        self.catch_ctrl_c()
        scluster.start(create=create, create_only=create_only, validate=False)
        if self.opts.login_master:
            scluster.ssh_to_master()
