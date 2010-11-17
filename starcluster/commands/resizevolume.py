#!/usr/bin/env python
from starcluster import volume
from starcluster import static

from createvolume import CmdCreateVolume


class CmdResizeVolume(CmdCreateVolume):
    """
    resizevolume [options] <volume_id> <volume_size>

    Resize an existing EBS volume

    NOTE: The EBS volume must either be unpartitioned or contain only a single
    partition. Any other configuration will be aborted.
    """

    names = ['resizevolume', 'res']

    def addopts(self, parser):
        parser.add_option(
            "-k", "--keypair", dest="keypair",
            action="store", type="string", default=None,
            help="The keypair to use when launching host instance " + \
            "(must be defined in the config)")
        parser.add_option(
            "-H", "--host-instance", dest="host_instance",
            action="store", type="string", default=None,
            help="Use existing instance as volume host rather than " + \
            "launching a new host")
        parser.add_option(
            "-s", "--shutdown-volume-host", dest="shutdown_instance",
            action="store_false", default=False,
            help="Shutdown volume host instance after creating volume")
        parser.add_option(
            "-i", "--image-id", dest="image_id",
            action="store", type="string", default=None,
            help="The AMI to use when launching volume host instance")
        parser.add_option(
            "-I", "--instance-type", dest="instance_type",
            action="store", type="choice", default="m1.small",
            choices=static.INSTANCE_TYPES.keys(),
            help="The instance type to use when launching volume" + \
            "host instance")
        parser.add_option(
            "-r", "--resizefs-cmd", dest="resizefs_cmd",
            action="store", type="string", default="resize2fs",
            help="Specify alternate resizefs command to use when " + \
            "formatting volume (default: resize2fs)")

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                "you must specify a volume id and a size (in GB)")
        volid, size = args
        key = self.opts.keypair
        host_instance = None
        if self.opts.host_instance:
            host_instance = self.ec2.get_instance(self.opts.host_instance)
            key = host_instance.key_name
        keypair, key_location = self._load_keypair(key)
        kwargs = self.specified_options_dict
        kwargs.update(dict(keypair=keypair, key_location=key_location,
                           host_instance=host_instance))
        vc = volume.VolumeCreator(self.ec2, **kwargs)
        vol = self.ec2.get_volume(volid)
        self.catch_ctrl_c()
        new_volid = vc.resize(vol, size)
        if new_volid:
            self.log.info(
                "Volume %s was successfully resized to %sGB" % (volid, size))
            self.log.info("New volume id is: %s" % new_volid)
        else:
            self.log.error("failed to resize volume %s" % volid)
