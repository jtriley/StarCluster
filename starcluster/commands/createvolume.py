import os

from starcluster import node
from starcluster import volume
from starcluster import static
from starcluster import exception

from base import CmdBase


class CmdCreateVolume(CmdBase):
    """
    createvolume [options] <volume_size> <volume_zone>

    Create a new EBS volume for use with StarCluster
    """

    names = ['createvolume', 'cv']

    def addopts(self, parser):
        parser.add_option(
            "-n", "--name", dest="name", action="store", type="string",
            default=None, help="Give the volume a user-friendly name "
            "(displayed in listvolumes command and in AWS console)")
        parser.add_option(
            "-b", "--bid", dest="spot_bid", action="store", type="float",
            default=None, help="Requests spot instances instead of flat "
            "rate instances. Uses SPOT_BID as max bid for the request.")
        parser.add_option(
            "-k", "--keypair", dest="keypair",
            action="store", type="string", default=None,
            help="The keypair to use when launching host instance "
            "(must be defined in the config)")
        parser.add_option(
            "-H", "--host-instance", dest="host_instance",
            action="store", type="string", default=None,
            help="Use specified instance as volume host rather than "
            "launching a new host")
        parser.add_option(
            "-d", "--detach-volume", dest="detach_vol",
            action="store_true", default=False,
            help="Detach new volume from host instance after creation")
        parser.add_option(
            "-s", "--shutdown-volume-host", dest="shutdown_instance",
            action="store_true", default=False,
            help="Shutdown host instance after creating new volume")
        parser.add_option(
            "-m", "--mkfs-cmd", dest="mkfs_cmd",
            action="store", type="string", default="mkfs.ext3",
            help="Specify alternate mkfs command to use when "
            "formatting volume (default: mkfs.ext3)")
        parser.add_option(
            "-i", "--image-id", dest="image_id",
            action="store", type="string", default=None,
            help="The AMI to use when launching volume host instance")
        parser.add_option(
            "-I", "--instance-type", dest="instance_type",
            action="store", type="choice", default="m1.small",
            choices=static.INSTANCE_TYPES.keys(),
            help="The instance type to use when launching volume "
            "host instance")
        parser.add_option(
            "-t", "--tag", dest="tags", action="callback", type="string",
            default={}, callback=self._build_dict,
            help="One or more tags to apply to the new volume (key=value)")

    def cancel_command(self, signum, frame):
        raise exception.CancelledCreateVolume()

    def _load_keypair(self, keypair=None):
        key_location = None
        if keypair:
            kp = self.ec2.get_keypair(keypair)
            key = self.cfg.get_key(kp.name)
            key_location = key.get('key_location', '')
        else:
            self.log.info("No keypair specified, picking one from config...")
            for kp in self.ec2.keypairs:
                if kp.name in self.cfg.keys:
                    keypair = kp.name
                    kl = self.cfg.get_key(kp.name).get('key_location', '')
                    if os.path.exists(kl) and os.path.isfile(kl):
                        self.log.info('Using keypair: %s' % keypair)
                        key_location = kl
                        break
        if not keypair:
            raise exception.ConfigError(
                "no keypairs in region %s defined in config" %
                self.ec2.region.name)
        if not key_location:
            raise exception.ConfigError(
                "cannot determine key_location for keypair %s" % keypair)
        if not os.path.exists(key_location):
            raise exception.ValidationError(
                "key_location '%s' does not exist." % key_location)
        elif not os.path.isfile(key_location):
            raise exception.ValidationError(
                "key_location '%s' is not a file." % key_location)
        return (keypair, key_location)

    def _get_size_arg(self, size):
        errmsg = "size argument must be an integer >= 1"
        try:
            size = int(size)
            if size <= 0:
                self.parser.error(errmsg)
            return size
        except ValueError:
            self.parser.error(errmsg)

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                "you must specify a size (in GB) and an availability zone")
        size, zone = args
        size = self._get_size_arg(size)
        zone = self.ec2.get_zone(zone).name
        key = self.opts.keypair
        host_instance = None
        if self.opts.host_instance:
            host_instance = self.ec2.get_instance(self.opts.host_instance)
            key = host_instance.key_name
        keypair, key_location = self._load_keypair(key)
        if host_instance:
            host_instance = node.Node(host_instance, key_location,
                                      alias="volumecreator_host")
        kwargs = self.specified_options_dict
        kwargs.update(dict(keypair=keypair, key_location=key_location,
                           host_instance=host_instance))
        vc = volume.VolumeCreator(self.ec2, **kwargs)
        if host_instance:
            vc._validate_host_instance(host_instance, zone)
        self.catch_ctrl_c()
        vc.create(size, zone, name=self.opts.name, tags=self.opts.tags)
