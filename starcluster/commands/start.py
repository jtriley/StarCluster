# Copyright 2009-2013 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import time

from starcluster import static
from starcluster import exception
from starcluster import completion
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

    def addopts(self, parser):
        templates = []
        if self.cfg:
            templates = self.cfg.clusters.keys()
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
        if completion:
            opt.completer = completion.ListCompleter(opt.choices)
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
        if completion:
            opt.completer = completion.ListCompleter(opt.choices)
        parser.add_option("-m", "--master-image-id", dest="master_image_id",
                          action="store", type="string", default=None,
                          help="AMI to use when launching master")
        parser.add_option("-n", "--node-image-id", dest="node_image_id",
                          action="store", type="string", default=None,
                          help="AMI to use when launching nodes")
        parser.add_option("-I", "--master-instance-type",
                          dest="master_instance_type", action="store",
                          choices=sorted(static.INSTANCE_TYPES.keys()),
                          default=None, help="instance type for the master "
                          "instance")
        opt = parser.add_option("-i", "--node-instance-type",
                                dest="node_instance_type", action="store",
                                choices=sorted(static.INSTANCE_TYPES.keys()),
                                default=None,
                                help="instance type for the node instances")
        if completion:
            opt.completer = completion.ListCompleter(opt.choices)
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
        parser.add_option("-U", "--userdata-script", dest="userdata_scripts",
                          action="append", default=None, metavar="FILE",
                          help="Path to userdata script that will run on "
                          "each node on start-up. Can be used multiple times.")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a <cluster_tag>")
        tag = args[0]
        create = not self.opts.no_create
        scluster = self.cm.get_cluster_group_or_none(tag)
        if scluster and create:
            scluster = self.cm.get_cluster(tag, group=scluster,
                                           load_receipt=False,
                                           require_keys=False)
            stopped_ebs = scluster.is_cluster_stopped()
            is_ebs = False
            if not stopped_ebs:
                is_ebs = scluster.is_ebs_cluster()
            raise exception.ClusterExists(tag, is_ebs=is_ebs,
                                          stopped_ebs=stopped_ebs)
        if not create and not scluster:
            raise exception.ClusterDoesNotExist(tag)
        create_only = self.opts.create_only
        validate = self.opts.validate
        validate_running = self.opts.no_create
        validate_only = self.opts.validate_only
        if scluster:
            scluster = self.cm.get_cluster(tag, group=scluster)
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
            if interval is not None:
                scluster.refresh_interval = interval
        if self.opts.spot_bid is not None and not self.opts.no_create:
            msg = user_msgs.spotmsg % {'size': scluster.cluster_size,
                                       'tag': tag}
            if not validate_only and not create_only:
                self.warn_experimental(msg, num_secs=5)
        try:
            scluster.start(create=create, create_only=create_only,
                           validate=validate, validate_only=validate_only,
                           validate_running=validate_running)
        except KeyboardInterrupt:
            if validate_only:
                raise
            else:
                raise exception.CancelledStartRequest(tag)
        if validate_only:
            return
        if not create_only and not self.opts.login_master:
            log.info(user_msgs.cluster_started_msg %
                     dict(tag=scluster.cluster_tag),
                     extra=dict(__textwrap__=True, __raw__=True))
        if self.opts.login_master:
            scluster.ssh_to_master()
