#!/usr/bin/env python
import time
import string
import cPickle

from starcluster import static
from starcluster import utils
from starcluster import exception
from starcluster.node import Node
from starcluster.spinner import Spinner
from starcluster.utils import print_timing
from starcluster.logger import log, INFO_NO_NEWLINE


class VolumeCreator(object):
    """
    Handles creating, partitioning, and formatting a new EBS volume.
    By default this class will create a single partition the size of the volume
    and format the partition using the ext3 filesystem.

    A host instance is needed in order to partition and format a new EBS
    volume. This class will look for host instances in the @sc-volumecreator
    security group. If it can't find an instance in that group that matches the
    zone of the new volume, a new instance is launched. By default the
    VolumeCreator class will not shutdown the host instance after creating a
    new volume. To shutdown the host instance after volume creation pass
    shutdown_instance=True.
    """
    def __init__(self, ec2_conn, keypair=None, key_location=None,
                 device='/dev/sdz', image_id=static.BASE_AMI_32,
                 instance_type="m1.small", shutdown_instance=False,
                 mkfs_cmd='mkfs.ext3'):
        self._ec2 = ec2_conn
        self._keypair = keypair
        self._key_location = key_location
        self._resv = None
        self._instance = None
        self._volume = None
        self._device = device or '/dev/sdz'
        self._node = None
        self._image_id = image_id or static.BASE_AMI_32
        self._instance_type = instance_type or 'm1.small'
        self._shutdown = shutdown_instance
        self._security_group = None
        self._mkfs_cmd = mkfs_cmd

    def __repr__(self):
        return "<VolumeCreator: %s>" % self._mkfs_cmd

    def __getstate__(self):
        return {}

    @property
    def security_group(self):
        if not self._security_group:
            sg = self._ec2.get_or_create_group(static.VOLUME_GROUP,
                                               cPickle.dumps(self),
                                               auth_ssh=True)
            self._security_group = sg
        return self._security_group

    def _request_instance(self, zone):
        alias = 'volume_host-%s' % zone
        for i in self.security_group.instances():
            if i.state in ['pending', 'running'] and i.placement == zone:
                log.info("Using existing instance %s in group %s" % \
                         (i.id, self.security_group.name))
                self._instance = Node(i, self._key_location, alias)
                break
        if not self._instance:
            log.info(
                "No instance in group %s for zone %s, launching one now." % \
                     (self.security_group.name, zone))
            self._resv = self._ec2.run_instances(
                image_id=self._image_id,
                instance_type=self._instance_type,
                min_count=1, max_count=1,
                security_groups=[self.security_group.name],
                key_name=self._keypair,
                placement=zone,
                user_data=alias)
            instance = self._resv.instances[0]
            self._instance = Node(instance, self._key_location, alias)
        s = Spinner()
        log.log(INFO_NO_NEWLINE,
                 "Waiting for instance %s to come up..." % self._instance.id)
        s.start()
        while not self._instance.is_up():
            time.sleep(15)
        s.stop()
        return self._instance

    def _create_volume(self, size, zone):
        vol = self._ec2.create_volume(size, zone)
        while vol.status != 'available':
            time.sleep(5)
            vol.update()
        self._volume = vol
        return self._volume

    def _determine_device(self):
        block_dev_map = self._instance.block_device_mapping
        for char in string.lowercase[::-1]:
            dev = '/dev/sd%s' % char
            if not block_dev_map.get(dev):
                self._device = dev
                return self._device

    def _attach_volume(self, instance_id, device):
        vol = self._volume
        vol.attach(instance_id, device)
        while True:
            vol.update()
            if vol.attachment_state() == 'attached':
                break
            time.sleep(5)
        return self._volume

    def _validate_image(self, image):
        i = self._ec2.get_image(image)
        if not i or i.id != image:
            raise exception.ValidationError(
                'image %s does not exist' % image)

    def _validate_zone(self, zone):
        z = self._ec2.get_zone(zone)
        if not z:
            raise exception.ValidationError(
                'zone %s does not exist' % zone)
        if z.state != 'available':
            log.warn('zone %s is not available at this time' % zone)
        return True

    def _validate_size(self, size):
        try:
            volume_size = int(size)
            if volume_size < 1:
                raise exception.ValidationError(
                    "volume_size must be an integer >= 1")
        except ValueError:
            raise exception.ValidationError("volume_size must be an integer")

    def _validate_device(self, device):
        if not utils.is_valid_device(device):
            raise exception.ValidationError("volume device %s is not valid" % \
                                            device)

    def _validate_required_progs(self, progs):
        log.info("Checking for required remote commands...")
        self._instance.ssh.check_required(progs)

    def validate(self, size, zone, device, image):
        self._validate_size(size)
        self._validate_zone(zone)
        self._validate_device(device)
        self._validate_image(image)

    def is_valid(self, size, zone, device, image):
        try:
            self.validate(size, zone, device, image)
            return True
        except exception.ValidationError, e:
            log.error(e.msg)
            return False

    def _partition_volume(self):
        self._instance.ssh.execute('echo ",,L" | sfdisk %s' % self._device,
                                   silent=False)

    def _format_volume_partitions(self):
        self._instance.ssh.execute('%s %s' % (self._mkfs_cmd,
                                              self._device + '1'),
                                   silent=False)

    @print_timing("Creating volume")
    def create(self, volume_size, volume_zone):
        self.validate(volume_size, volume_zone, self._device, self._image_id)
        try:
            log.info(("Requesting host instance in zone %s to attach " + \
                      "volume to...") % volume_zone)
            instance = self._request_instance(volume_zone)
            self._validate_required_progs([self._mkfs_cmd, 'sfdisk'])
            self._determine_device()
            log.info("Creating %sGB volume in zone %s" % (volume_size,
                                                          volume_zone))
            vol = self._create_volume(volume_size, volume_zone)
            log.info("New volume id: %s" % vol.id)
            log.info("Attaching volume to instance %s" % instance.id)
            self._attach_volume(instance.id, self._device)
            log.info("Partitioning the volume")
            self._partition_volume()
            log.info("Formatting volume")
            self._format_volume_partitions()
            if self._shutdown:
                log.info("Detaching volume %s from instance %s" % \
                         (vol.id, self._instance.id))
                vol.detach()
                time.sleep(5)
                for i in self.security_group.instances():
                    log.info("Shutting down instance %s" % i.id)
                    i.terminate()
                log.info("Removing security group %s" % \
                         self.security_group.name)
                self.security_group.delete()
            else:
                log.info(("The volume host instance %s is still running. " + \
                          "Run 'starcluster stop volumecreator' to shut " + \
                          "down all volume host instances manually.") % \
                         self._instance.id)
            return vol.id
        except Exception:
            if self._volume:
                log.error(
                    "Error occured, detaching, and deleting volume: %s" % \
                    self._volume.id)
                self._volume.detach(force=True)
                time.sleep(5)
                self._volume.delete()
            i = self._instance
            if i and i.state in ['running', 'pending']:
                log.info(("The volume host instance %s is still running. " + \
                          "Run 'starcluster stop volumecreator' to shut " + \
                          "down all volume host instances manually.") % i.id)
            raise
