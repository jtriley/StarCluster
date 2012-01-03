import time

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
    default use the -c (--cluster-template) option:

        $ starcluster start -c largecluster mynewcluster

    This will launch a cluster named "mynewcluster" using the settings from
    the "largecluster" cluster template instead of the default template.
    """
    names = ['start']

    tag = None

    def addopts(self, parser):
        templates = []
        if self.cfg:
            templates = self.cfg.get_cluster_names().keys()
        parser.add_option("-x", "--no-create", dest="no_create",
                          action="store_true", default=False,
                          help="do not launch new EC2 instances when "
                          "starting cluster (use existing instances instead)")
        parser.add_option("-o", "--create-only", dest="create_only",
                          action="store_true", default=False,
                          help="only launch/start EC2 instances, "
                          "do not perform any setup routines")
        parser.add_option("-v", "--validate-only", dest="validate_only",
                          action="store_true", default=False,
                          help="only validate cluster settings, do "
                          "not start a cluster")
        parser.add_option("-V", "--skip-validation", dest="validate",
                          action="store_false", default=True,
                          help="do not validate cluster settings")
        parser.add_option("-l", "--login-master", dest="login_master",
                          action="store_true", default=False,
                          help="login to master node after launch")
        parser.add_option("-q", "--disable-queue", dest="disable_queue",
                          action="store_true", default=None,
                          help="do not configure a queueing system (SGE)")
        parser.add_option("--force-spot-master",
                          dest="force_spot_master", action="store_true",
                          default=None, help="when creating a spot cluster "
                          "the default is to launch the master as "
                          "a flat-rate instance for stability. this option "
                          "forces launching the master node as a spot "
                          "instance when a spot cluster is requested.")
        opt = parser.add_option("-c", "--cluster-template", action="store",
                                dest="cluster_template", choices=templates,
                                default=None, help="cluster template to use "
                                "from the config file")
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(opt.choices)
        parser.add_option("-r", "--refresh-interval", dest="refresh_interval",
                          type="int", action="callback", default=None,
                          callback=self._positive_int,
                          help="refresh interval when waiting for cluster "
                          "nodes to come up (default: 30)")
        parser.add_option("-b", "--bid", dest="spot_bid", action="store",
                          type="float", default=None,
                          help="requests spot instances instead of flat "
                          "rate instances. Uses SPOT_BID as max bid for "
                          "the request.")
        parser.add_option("-d", "--description", dest="cluster_description",
                          action="store", type="string",
                          default="Cluster requested at %s" %
                          time.strftime("%Y%m%d%H%M"),
                          help="brief description of cluster")
        parser.add_option("-s", "--cluster-size", dest="cluster_size",
                          action="callback", type="int", default=None,
                          callback=self._positive_int,
                          help="number of ec2 instances to launch")
        parser.add_option("-u", "--cluster-user", dest="cluster_user",
                          action="store", type="string", default=None,
                          help="name of user to create on cluster "
                          "(defaults to sgeadmin)")
        opt = parser.add_option("-S", "--cluster-shell", dest="cluster_shell",
                                action="store",
                                choices=static.AVAILABLE_SHELLS.keys(),
                                default=None,
                                help="shell for cluster user "
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
                          help="instance type for the master instance")
        opt = parser.add_option("-i", "--node-instance-type",
                                dest="node_instance_type", action="store",
                                choices=static.INSTANCE_TYPES.keys(),
                                default=None,
                                help="instance type for the node instances")
        if optcomplete:
            opt.completer = optcomplete.ListCompleter(opt.choices)
        parser.add_option("-a", "--availability-zone",
                          dest="availability_zone", action="store",
                          type="string", default=None,
                          help="availability zone to launch instances in")
        parser.add_option("-k", "--keyname", dest="keyname", action="store",
                          type="string", default=None,
                          help="name of the keypair to use when "
                          "launching the cluster")
        parser.add_option("-K", "--key-location", dest="key_location",
                          action="store", type="string", default=None,
                          metavar="FILE",
                          help="path to an ssh private key that matches the "
                          "cluster keypair")

    def cancel_command(self, signum, frame):
        raise exception.CancelledStartRequest(self.tag)

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a <cluster_tag>")
        tag = self.tag = args[0]
        create = not self.opts.no_create
        create_only = self.opts.create_only
        scluster = self.cm.get_cluster_or_none(tag, require_keys=False)
        validate = self.opts.validate
        validate_running = self.opts.no_create
        validate_only = self.opts.validate_only
        if scluster and create:
            stopped_ebs = scluster.is_cluster_stopped()
            is_ebs = False
            if not stopped_ebs:
                is_ebs = scluster.is_ebs_cluster()
            raise exception.ClusterExists(tag, is_ebs=is_ebs,
                                          stopped_ebs=stopped_ebs)
        if not scluster and not create:
            raise exception.ClusterDoesNotExist(tag)
        elif scluster:
            validate_running = True
        else:
            template = self.opts.cluster_template
            if not template:
                try:
                    template = self.cm.get_default_cluster_template()
                except exception.NoDefaultTemplateFound, e:
                    try:
                        ctmpl = e.options[0]
                    except IndexError:
                        ctmpl = "smallcluster"
                    e.msg += " \n\nAlternatively, you can specify a cluster "
                    e.msg += "template to use by passing the '-c' option to "
                    e.msg += "the 'start' command, e.g.:\n\n"
                    e.msg += "    $ starcluster start -c %s %s" % (ctmpl, tag)
                    raise e
                log.info("Using default cluster template: %s" % template)
            scluster = self.cm.get_cluster_template(template, tag)
        scluster.update(self.specified_options_dict)
        if self.opts.keyname and not self.opts.key_location:
            key = self.cfg.get_key(self.opts.keyname)
            scluster.key_location = key.key_location
        if not self.opts.refresh_interval:
            interval = self.cfg.globals.get("refresh_interval")
            scluster.refresh_interval = interval
        if self.opts.spot_bid is not None and not self.opts.no_create:
            msg = user_msgs.spotmsg % {'size': scluster.cluster_size,
                                       'tag': tag}
            if not validate_only and not create_only:
                self.warn_experimental(msg, num_secs=5)
        self.catch_ctrl_c()
        scluster.start(create=create, create_only=create_only,
                       validate=validate, validate_only=validate_only,
                       validate_running=validate_running)
        if validate_only:
            return
        if not create_only and not self.opts.login_master:
            log.info(user_msgs.cluster_started_msg %
                     dict(tag=scluster.cluster_tag),
                     extra=dict(__textwrap__=True, __raw__=True))
        if self.opts.login_master:
            scluster.ssh_to_master()
