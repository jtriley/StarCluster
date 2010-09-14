#!/usr/bin/env python

from starcluster import exception
from starcluster import volume
from starcluster.logger import log

from base import CmdBase

class CmdCreateVolume(CmdBase):
    """
    createvolume [options] <volume_size> <volume_zone>

    Create a new EBS volume for use with StarCluster
    """

    names = ['createvolume', 'cv']

    def addopts(self, parser):
        opt = parser.add_option(
            "-i","--image-id", dest="image_id",
            action="store", type="string", default=None,
            help="The AMI to use when launching volume host instance")
        opt = parser.add_option(
            "-I","--instance-type", dest="instance_type",
            action="store", type="string", default=None,
            help="The instance type to use when launching volume host instance")
        opt = parser.add_option(
            "-n","--no-shutdown", dest="shutdown_instance",
            action="store_false", default=True,
            help="Do not shutdown volume host instance after creating volume")
        opt = parser.add_option(
            "-m","--mkfs-cmd", dest="mkfs_cmd",
            action="store", type="string", default="mkfs.ext3",
            help="Specify alternate mkfs command to use when formatting volume" +\
            "(default: mkfs.ext3)")
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
