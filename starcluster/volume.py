import time
import string

from starcluster import static
from starcluster import utils
from starcluster import exception
from starcluster import cluster
from starcluster.utils import print_timing
from starcluster.logger import log


class VolumeCreator(cluster.Cluster):
    """
    Handles creating, partitioning, and formatting a new EBS volume.
    By default this class will format the entire drive (without partitioning)
    using the ext3 filesystem.

    host_instance - EC2 instance to use when formatting volume. must exist in
    the same zone as the new volume. if not specified this class will look for
    host instances in the @sc-volumecreator security group.  If it can't find
    an instance in the @sc-volumecreator group that matches the zone of the
    new volume, a new instance is launched.

    shutdown_instance - True will shutdown the host instance after volume
    creation
    """
    def __init__(self, ec2_conn, spot_bid=None, keypair=None,
                 key_location=None, host_instance=None, device='/dev/sdz',
                 image_id=static.BASE_AMI_32, instance_type="m1.small",
                 shutdown_instance=False, detach_vol=False,
                 mkfs_cmd='mkfs.ext3', resizefs_cmd='resize2fs', **kwargs):
        self._host_instance = host_instance
        self._instance = None
        self._volume = None
        self._device = device or '/dev/sdz'
        self._image_id = image_id or static.BASE_AMI_32
        self._instance_type = instance_type or 'm1.small'
        self._shutdown = shutdown_instance
        self._detach_vol = detach_vol
        self._mkfs_cmd = mkfs_cmd
        self._resizefs_cmd = resizefs_cmd
        self._alias_tmpl = "volhost-%s"
        super(VolumeCreator, self).__init__(
            ec2_conn=ec2_conn, spot_bid=spot_bid, keyname=keypair,
            key_location=key_location, cluster_tag=static.VOLUME_GROUP_NAME,
            cluster_size=1, cluster_user="sgeadmin", cluster_shell="bash",
            node_image_id=self._image_id,
            node_instance_type=self._instance_type)

    def __repr__(self):
        return "<VolumeCreator: %s>" % self._mkfs_cmd

    def _get_existing_instance(self, zone):
        """
        Returns any existing instance in the @sc-volumecreator group that's
        located in zone.
        """
        active_states = ['pending', 'running']
        i = self._host_instance
        if i and self._validate_host_instance(i, zone):
            log.info("Using specified host instance %s" % i.id)
            return i
        for node in self.nodes:
            if node.state in active_states and node.placement == zone:
                log.info("Using existing instance %s in group %s" %
                         (node.id, self.cluster_group.name))
                return node

    def _request_instance(self, zone):
        self._instance = self._get_existing_instance(zone)
        if not self._instance:
            alias = self._alias_tmpl % zone
            self._validate_image_and_type(self._image_id, self._instance_type)
            log.info(
                "No instance in group %s for zone %s, launching one now." %
                (self.cluster_group.name, zone))
            self._resv = self.create_node(alias, image_id=self._image_id,
                                          instance_type=self._instance_type,
                                          zone=zone)
            self.wait_for_cluster(msg="Waiting for volume host to come up...")
            self._instance = self.get_node_by_alias(alias)
        else:
            s = self.get_spinner("Waiting for instance %s to come up..." %
                                 self._instance.id)
            while not self._instance.is_up():
                time.sleep(self.refresh_interval)
            s.stop()
        return self._instance

    def _create_volume(self, size, zone, snapshot_id=None):
        msg = "Creating %sGB volume in zone %s" % (size, zone)
        if snapshot_id:
            msg += " from snapshot %s" % snapshot_id
        log.info(msg)
        vol = self.ec2.create_volume(size, zone, snapshot_id)
        log.info("New volume id: %s" % vol.id)
        s = self.get_spinner("Waiting for new volume to become 'available'...")
        while vol.status != 'available':
            time.sleep(5)
            vol.update()
        s.stop()
        self._volume = vol
        return self._volume

    def _determine_device(self):
        block_dev_map = self._instance.block_device_mapping
        for char in string.lowercase[::-1]:
            dev = '/dev/sd%s' % char
            if not block_dev_map.get(dev):
                self._device = dev
                return self._device

    def _attach_volume(self, vol, instance_id, device):
        s = self.get_spinner("Attaching volume %s to instance %s..." %
                             (vol.id, instance_id))
        vol.attach(instance_id, device)
        while True:
            vol.update()
            if vol.attachment_state() == 'attached':
                break
            time.sleep(5)
        s.stop()
        return self._volume

    def _validate_host_instance(self, instance, zone):
        if instance.state not in ['pending', 'running']:
            raise exception.InstanceNotRunning(instance.id)
        if instance.placement != zone:
            raise exception.ValidationError(
                "specified host instance %s is not in zone %s" %
                (instance.id, zone))
        return True

    def _validate_image_and_type(self, image, itype):
        img = self.ec2.get_image_or_none(image)
        if not img:
            raise exception.ValidationError(
                'image %s does not exist' % image)
        if not itype in static.INSTANCE_TYPES:
            choices = ', '.join(static.INSTANCE_TYPES)
            raise exception.ValidationError(
                'instance_type must be one of: %s' % choices)
        itype_platform = static.INSTANCE_TYPES.get(itype)
        img_platform = img.architecture
        if img_platform not in itype_platform:
            error_msg = "instance_type %(itype)s is for an "
            error_msg += "%(iplat)s platform while image_id "
            error_msg += "%(img)s is an %(imgplat)s platform"
            error_msg %= {'itype': itype, 'iplat': ', '.join(itype_platform),
                          'img': img.id, 'imgplat': img_platform}
            raise exception.ValidationError(error_msg)

    def _validate_zone(self, zone):
        z = self.ec2.get_zone(zone)
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
            raise exception.ValidationError("volume device %s is not valid" %
                                            device)

    def _validate_required_progs(self, progs):
        log.info("Checking for required remote commands...")
        self._instance.ssh.check_required(progs)

    def validate(self, size, zone, device):
        self._validate_size(size)
        self._validate_zone(zone)
        self._validate_device(device)

    def is_valid(self, size, zone, device):
        try:
            self.validate(size, zone, device)
            return True
        except exception.BaseException, e:
            log.error(e.msg)
            return False

    def _partition_volume(self):
        self._instance.ssh.execute('echo ",,L" | sfdisk %s' % self._device,
                                   silent=False)

    def _format_volume(self):
        log.info("Formatting volume...")
        self._instance.ssh.execute('%s -F %s' % (self._mkfs_cmd, self._device),
                                   silent=False)

    def _warn_about_volume_hosts(self):
        sg = self.ec2.get_group_or_none(static.VOLUME_GROUP)
        if not sg:
            return
        vol_hosts = filter(lambda x: x.state in ['running', 'pending'],
                           sg.instances())
        vol_hosts = map(lambda x: x.id, vol_hosts)
        if vol_hosts:
            log.warn("There are still volume hosts running: %s" %
                     ', '.join(vol_hosts))
            log.warn("Run 'starcluster terminate %s' to terminate *all* "
                     "volume host instances once they're no longer needed" %
                     static.VOLUME_GROUP_NAME)
        else:
            log.info("No active volume hosts found. Run 'starcluster "
                     "terminate %(g)s' to remove the '%(g)s' group" %
                     {'g': static.VOLUME_GROUP_NAME})

    def shutdown(self):
        vol = self._volume
        host = self._instance
        if self._detach_vol:
            log.info("Detaching volume %s from instance %s" %
                     (vol.id, host.id))
            vol.detach()
        else:
            log.info("Leaving volume %s attached to instance %s" %
                     (vol.id, host.id))
        if self._shutdown:
            log.info("Terminating host instance %s" % host.id)
            host.terminate()
        else:
            log.info("Not terminating host instance %s" %
                     host.id)

    @print_timing("Creating volume")
    def create(self, volume_size, volume_zone, name=None, tags=None):
        try:
            self.validate(volume_size, volume_zone, self._device)
            instance = self._request_instance(volume_zone)
            self._validate_required_progs([self._mkfs_cmd.split()[0]])
            self._determine_device()
            vol = self._create_volume(volume_size, volume_zone)
            if tags:
                for tag in tags:
                    tagval = tags.get(tag)
                    tagmsg = "Adding volume tag: %s" % tag
                    if tagval:
                        tagmsg += "=%s" % tagval
                    log.info(tagmsg)
                    vol.add_tag(tag, tagval)
            if name:
                vol.add_tag("Name", name)
            self._attach_volume(self._volume, instance.id, self._device)
            self._format_volume()
            self.shutdown()
            self._warn_about_volume_hosts()
            log.info("Your new %sGB volume %s has been created successfully" %
                     (volume_size, vol.id))
            return vol
        except Exception:
            log.error("failed to create new volume")
            if self._volume:
                log.error(
                    "Error occurred. Detaching, and deleting volume: %s" %
                    self._volume.id)
                self._volume.detach(force=True)
                time.sleep(5)
                self._volume.delete()
            self._warn_about_volume_hosts()
            raise

    def _validate_resize(self, vol, size):
        self._validate_size(size)
        if vol.size > size:
            log.warn("You are attempting to shrink an EBS volume. "
                     "Data loss may occur")

    def resize(self, vol, size, dest_zone=None):
        """
        Resize EBS volume

        vol - boto volume object
        size - new volume size
        dest_zone - zone to create the new resized volume in. this must be
        within the original volume's region otherwise a manual copy (rsync)
        is required. this is currently not implemented.
        """
        try:
            self._validate_device(self._device)
            self._validate_resize(vol, size)
            zone = vol.zone
            if dest_zone:
                self._validate_zone(dest_zone)
                zone = dest_zone
            host = self._request_instance(zone)
            self._validate_required_progs([self._resizefs_cmd.split()[0]])
            self._determine_device()
            snap = self.ec2.create_snapshot(vol, wait_for_snapshot=True)
            new_vol = self._create_volume(size, zone, snap.id)
            self._attach_volume(new_vol, host.id, self._device)
            devs = filter(lambda x: x.startswith(self._device),
                          host.ssh.ls('/dev'))
            device = self._device
            if len(devs) == 1:
                log.info("No partitions found, resizing entire device")
            elif len(devs) == 2:
                log.info("One partition found, resizing partition...")
                self._partition_volume()
                device += '1'
            else:
                raise exception.InvalidOperation(
                    "EBS volume %s has more than 1 partition. "
                    "You must resize this volume manually" % vol.id)
            host.ssh.execute(' '.join([self._resizefs_cmd, device]))
            log.info("Removing generated snapshot %s" % snap.id)
            snap.delete()
            self.shutdown()
            self._warn_about_volume_hosts()
            return new_vol.id
        except Exception:
            self._warn_about_volume_hosts()
            raise
