import os
import time
import string

from starcluster import ssh
from starcluster import utils
from starcluster import exception
from starcluster.spinner import Spinner
from starcluster.utils import print_timing
from starcluster.logger import log


class ImageCreator(object):
    """
    Base class for S3/EBS Image Creators. Handles fetching the host and setting
    up a connection object as well as setting common attributes (description,
    kernel_id, ramdisk_id)

    easy_ec2 must be an awsutils.EasyEC2 object

    instance_id is the id of the instance to be imaged

    key_location must point to the private key file corresponding to the
    keypair used to launch instance_id
    """
    def __init__(self, easy_ec2, instance_id, key_location, description=None,
                 kernel_id=None, ramdisk_id=None):
        self.ec2 = easy_ec2
        self.host = self.ec2.get_instance(instance_id)
        if self.host.state != 'running':
            raise exception.InstanceNotRunning(self.host.id, self.host.state,
                                               self.host.dns_name)
        self.host_ssh = ssh.SSHClient(self.host.dns_name, username='root',
                                      private_key=key_location)
        self.description = description
        self.kernel_id = kernel_id or self.host.kernel
        self.ramdisk_id = ramdisk_id or self.host.ramdisk

    def clean_private_data(self):
        log.info('Removing private data...')
        conn = self.host_ssh
        conn.execute('find /home -maxdepth 1 -type d -exec rm -rf {}/.ssh \;')
        conn.execute('rm -f /var/log/secure')
        conn.execute('rm -f /var/log/lastlog')
        conn.execute('rm -rf /root/*')
        conn.execute('rm -f ~/.bash_history')
        conn.execute('rm -rf /tmp/*')
        conn.execute('rm -rf /root/*.hist*')
        conn.execute('rm -rf /var/log/*.gz')


class S3ImageCreator(ImageCreator):
    """
    Class for creating a new instance-store AMI from a running instance
    """
    def __init__(self, easy_ec2, instance_id, key_location, aws_user_id,
                 ec2_cert, ec2_private_key, bucket, image_name='image',
                 description=None, kernel_id=None, ramdisk_id=None,
                 remove_image_files=False, **kwargs):
        super(S3ImageCreator, self).__init__(easy_ec2, instance_id,
                                             key_location, description,
                                             kernel_id, ramdisk_id)
        self.userid = aws_user_id
        self.cert = ec2_cert
        self.private_key = ec2_private_key
        self.bucket = bucket
        self.prefix = image_name
        self.description = description
        self.remove_image_files = remove_image_files
        for name in self.bucket.split("/"):
            if not utils.is_valid_bucket_name(name):
                raise exception.InvalidBucketName(self.bucket)
        if not utils.is_valid_image_name(self.prefix):
            raise exception.InvalidImageName(self.prefix)
        if not self.cert:
            try:
                self.cert = os.environ['EC2_CERT']
            except KeyError:
                raise exception.EC2CertRequired()
        if not self.private_key:
            try:
                self.private_key = os.environ['EC2_PRIVATE_KEY']
            except KeyError:
                raise exception.EC2PrivateKeyRequired()
        if not self.userid:
            raise exception.AWSUserIdRequired()
        if not os.path.exists(self.cert):
            raise exception.EC2CertDoesNotExist(self.cert)
        if not os.path.exists(self.private_key):
            raise exception.EC2PrivateKeyDoesNotExist(self.private_key)
        self.config_dict = {
            'access_key': self.ec2.aws_access_key_id,
            'secret_key': self.ec2.aws_secret_access_key,
            'private_key': os.path.split(self.private_key)[-1],
            'userid': self.userid,
            'cert': os.path.split(self.cert)[-1],
            'bucket': self.bucket,
            'prefix': self.prefix,
            'arch': self.host.architecture,
        }

    def __repr__(self):
        return "<S3ImageCreator: %s>" % self.host.id

    @print_timing
    def create_image(self):
        log.info("Checking for EC2 API tools...")
        self.host_ssh.check_required(['ec2-upload-bundle', 'ec2-bundle-vol'])
        self.ec2.s3.get_or_create_bucket(self.bucket)
        self._remove_image_files()
        self._bundle_image()
        self._upload_image()
        ami_id = self._register_image()
        if self.remove_image_files:
            self._remove_image_files()
        return ami_id

    def _remove_image_files(self):
        conn = self.host_ssh
        conn.execute('umount /mnt/img-mnt', ignore_exit_status=True)
        conn.execute('rm -rf /mnt/img-mnt')
        conn.execute('rm -rf /mnt/%(prefix)s*' % self.config_dict)

    def _transfer_pem_files(self):
        """copy pem files to /mnt on image host"""
        conn = self.host_ssh
        pkey_dest = "/mnt/" + os.path.basename(self.private_key)
        cert_dest = "/mnt/" + os.path.basename(self.cert)
        conn.put(self.private_key, pkey_dest)
        conn.put(self.cert, cert_dest)

    @print_timing
    def _bundle_image(self):
        # run script to prepare the host
        conn = self.host_ssh
        config_dict = self.config_dict
        self._transfer_pem_files()
        self.clean_private_data()
        log.info('Creating the bundled image: (please be patient)')
        conn.execute('ec2-bundle-vol -d /mnt -k /mnt/%(private_key)s '
                     '-c /mnt/%(cert)s -p %(prefix)s -u %(userid)s '
                     '-r %(arch)s -e /root/.ssh' % config_dict, silent=False)
        self._cleanup_pem_files()

    @print_timing
    def _upload_image(self):
        log.info('Uploading bundled image: (please be patient)')
        conn = self.host_ssh
        config_dict = self.config_dict
        conn.execute('ec2-upload-bundle -b %(bucket)s '
                     '-m /mnt/%(prefix)s.manifest.xml -a %(access_key)s '
                     '-s %(secret_key)s' % config_dict, silent=False)

    def _cleanup(self):
        #just in case...
        self._cleanup_pem_files()
        conn = self.host_ssh
        conn.execute('rm -f ~/.bash_history', silent=False)

    def _cleanup_pem_files(self):
        log.info('Cleaning up...')
        # delete keys and remove bash history
        conn = self.host_ssh
        conn.execute('rm -f /mnt/*.pem /mnt/*.pem', silent=False)

    def _register_image(self):
        # register image in s3 with ec2
        conn = self.ec2
        config_dict = self.config_dict
        return conn.register_image(
            self.prefix,
            description=self.description,
            image_location="%(bucket)s/%(prefix)s.manifest.xml" % config_dict,
            kernel_id=self.kernel_id,
            ramdisk_id=self.ramdisk_id,
            architecture=config_dict.get('arch'),
        )


class EBSImageCreator(ImageCreator):
    """
    Creates a new EBS image from a running instance

    If the instance is an instance-store image, then this class will create a
    new volume, attach it to the instance, sync the root filesystem to the
    volume, detach the volume, snapshot it, and then create a new AMI from the
    snapshot

    If the instance is EBS-backed, this class simply calls ec2.create_image
    which tells Amazon to create a new image in a single API call.
    """

    def __init__(self, easy_ec2, instance_id, key_location, name,
                 description=None, snapshot_description=None,
                 kernel_id=None, ramdisk_id=None, **kwargs):
        super(EBSImageCreator, self).__init__(easy_ec2, instance_id,
                                              key_location, description,
                                              kernel_id, ramdisk_id)
        self.name = name
        self.description = description
        self.snapshot_description = snapshot_description or description
        self._snap = None
        self._vol = None

    @print_timing
    def create_image(self, size=15):
        try:
            self.clean_private_data()
            if self.host.root_device_type == "ebs":
                return self._create_image_from_ebs(size)
            return self._create_image_from_instance_store(size)
        except:
            log.error("Error occurred while creating image")
            if self._snap:
                log.error("Removing generated snapshot '%s'" % self._snap)
                self._snap.delete()
            if self._vol:
                log.error("Removing generated volume '%s'" % self._vol.id)
                self._vol.detach(force=True)
                self._vol.delete()
            raise

    def _create_image_from_ebs(self, size=15):
        log.info("Creating EBS image...")
        imgid = self.ec2.create_image(self.host.id, self.name,
                                      self.description)
        log.info("Waiting for AMI %s to become available..." % imgid,
                 extra=dict(__nonewline__=True))
        img = self.ec2.get_image(imgid)
        s = Spinner()
        s.start()
        while img.state == "pending":
            time.sleep(15)
            if img.update() == "failed":
                raise exception.AWSError(
                    "EBS image creation failed for AMI %s" % imgid)
        s.stop()
        return imgid

    def _create_image_from_instance_store(self, size=15):
        host = self.host
        host_ssh = self.host_ssh
        log.info("Creating new EBS-backed image from instance-store instance")
        log.info("Creating new root volume...")
        vol = self._vol = self.ec2.create_volume(size, host.placement)
        log.info("Created new volume: %s" % vol.id)
        while vol.update() != 'available':
            time.sleep(5)
        dev = None
        for i in string.ascii_lowercase[::-1]:
            dev = '/dev/sd%s' % i
            if not dev in host.block_device_mapping:
                break
        log.info("Attaching volume %s to instance %s on %s" %
                 (vol.id, host.id, dev))
        vol.attach(host.id, dev)
        while vol.update() != 'in-use':
            time.sleep(5)
        while not host_ssh.path_exists(dev):
            time.sleep(5)
        host_ssh.execute('mkfs.ext3 -F %s' % dev)
        mount_point = '/ebs'
        while host_ssh.path_exists(mount_point):
            mount_point += '1'
        host_ssh.mkdir(mount_point)
        log.info("Mounting %s on %s" % (dev, mount_point))
        host_ssh.execute('mount %s %s' % (dev, mount_point))
        log.info("Configuring /etc/fstab")
        host_ssh.remove_lines_from_file('/etc/fstab', '/mnt')
        fstab = host_ssh.remote_file('/etc/fstab', 'a')
        fstab.write('/dev/sdb1 /mnt auto defaults,nobootwait 0 0\n')
        fstab.close()
        log.info("Syncing root filesystem to new volume (%s)" % vol.id)
        host_ssh.execute(
            'rsync -avx --exclude %(mpt)s --exclude /root/.ssh / %(mpt)s' %
            {'mpt': mount_point})
        log.info("Unmounting %s from %s" % (dev, mount_point))
        host_ssh.execute('umount %s' % mount_point)
        log.info("Detaching volume %s from %s" % (dev, mount_point))
        vol.detach()
        while vol.update() != 'available':
            time.sleep(5)
        sdesc = self.snapshot_description
        snap = self._snap = self.ec2.create_snapshot(vol,
                                                     description=sdesc,
                                                     wait_for_snapshot=True)
        log.info("New snapshot created: %s" % snap.id)
        log.info("Removing generated volume %s" % vol.id)
        vol.delete()
        log.info("Creating root block device map using snapshot %s" % snap.id)
        bmap = self.ec2.create_root_block_device_map(snap.id,
                                                     add_ephemeral_drives=True)
        log.info("Registering new image...")
        img_id = self.ec2.register_image(name=self.name,
                                         description=self.description,
                                         architecture=host.architecture,
                                         kernel_id=self.kernel_id,
                                         ramdisk_id=self.ramdisk_id,
                                         root_device_name='/dev/sda1',
                                         block_device_map=bmap)
        return img_id


# for backwards compatibility
EC2ImageCreator = S3ImageCreator
