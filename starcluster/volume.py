import time
from starcluster.logger import log
from starcluster.node import Node
from starcluster import static
from starcluster import utils
from starcluster import exception

class VolumeCreator(object):
    def __init__(self, cfg, add_to_cfg=False, keypair=None, device='/dev/sdz',
                 image_id=static.BASE_AMI_32, shutdown_instance=True):
        self._cfg = cfg
        self._ec2 = cfg.get_easy_ec2()
        self._keypair = keypair
        self._key_location = None
        self._add_to_cfg = add_to_cfg
        self._resv = None
        self._instance = None
        self._volume = None
        self._device = device or '/dev/sdz'
        self._node = None
        self._image_id = image_id or BASE_AMI_32
        self._shutdown = shutdown_instance

    def _request_instance(self):
        if not self._resv:
            self._resv = self._ec2.run_instances(image_id=self._image_id,
                instance_type='m1.small',
                min_count=1, max_count=1,
                key_name=self._keypair)
            instance = self._resv.instances[0]
            self._instance = Node(instance, self._key_location, 'vol_host')
            while not self._instance.is_up():
                time.sleep(15)
        return self._instance

    def _create_volume(self, size, zone):
        vol = self._ec2.conn.create_volume(size, zone)
        while True:
            vol.update()
            if vol.status == 'available':
                self._volume = vol
                break
            time.sleep(5)
        return self._volume

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
                'image %s does not exist' % image
            )

    def _validate_zone(self, zone):
        z = self._ec2.get_zone(zone)
        if not z:
            raise exception.ValidationError(
                'zone %s does not exist' % zone
            )
        if z.state != 'available':
            log.warn('zone %s is not available at this time' % zone)
        return True

    def _validate_size(self, size):
        try:
            volume_size = int(size)
        except ValueError:
            raise exception.ValidationError("volume_size must be an integer")

    def _validate_device(self, device):
        if not utils.is_valid_device(device):
            raise exception.ValidationError("volume device %s is not valid" % \
                                            device)

    def is_valid(self, size, zone, device, image):
        try:
            self._validate_size(size)
            self._validate_zone(zone)
            self._validate_device(device)
            self._validate_image(image)
            return True
        except exception.ValidationError,e:
            log.error(e.msg)
            return False

    def _partition_volume(self):
        self._instance.ssh.execute('echo ",,L" | sfdisk %s' % self._device,
                                   silent=False)

    def _format_volume_partitions(self):
        self._instance.ssh.execute('mkfs.ext3 %s' % (self._device + '1'),
                                   silent=False)

    def _load_keypair(self):
        kps = self._ec2.keypairs; cfg = self._cfg
        if self._keypair:
            for kp in kps:
                if kp.name == self._keypair and cfg.keys.get(kp.name):
                    log.info('Using keypair %s' % kp.name)
                    self._keypair = kp.name
                    self._key_location = cfg.keys.get(kp.name).get('key_location')
                    return
        for kp in kps:
            if self._cfg.keys.has_key(kp.name):
                log.info('Using keypair %s' % kp.name)
                self._keypair = kp.name
                self._key_location = cfg.keys.get(kp.name).get('key_location')
                return

    def create(self, volume_size, volume_zone):
        if self.is_valid(volume_size, volume_zone, self._device, self._image_id):
            #try:
            self._load_keypair()
            log.info("Creating %sGB volume in zone %s" % (volume_size,
                                                          volume_zone))
            vol = self._create_volume(volume_size, volume_zone)
            log.info("Requesting instance")
            instance = self._request_instance()
            log.info("Attaching volume to instance")
            self._attach_volume(instance.id, self._device)
            log.info("Partitioning the volume")
            self._partition_volume()
            log.info("Formatting volume")
            self._format_volume_partitions()
            if self._shutdown:
                vol.detach()
                time.sleep(5)
                instance.terminate()
            #except Exception,e:
                #log.error("exception thrown: %s" % e)
                #if self._volume:
                    #self._volume.detach()
                    #time.sleep(5)
                #if self._instance:
                    #self._instance.terminate()
