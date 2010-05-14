#!/usr/bin/env python
import os
import pickle
from optparse import OptionParser
from starcluster import awsutils
from starcluster import exception
from starcluster import utils
from starcluster import node
from starcluster.logger import log
from starcluster.utils import print_timing

def create_image(instanceid, image_name, bucket, cfg, **kwargs):
    instance = node.get_node(instanceid, cfg)
    if instance.state != 'running':
        raise exception.InstanceNotRunning(instance.id)
    kwargs.update(cfg.aws)
    kwargs.update({
        'instance': instance,
        'prefix': image_name,
        'bucket': bucket,
    })
    icreator = EC2ImageCreator(**kwargs)
    return icreator.create_image()

class EC2ImageCreator(object):
    """
    Class for creating a new AMI from a running instance

    instance must be a starcluster.node.Node instance
    """
    def __init__(self, instance=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_user_id=None, 
                 ec2_cert=None, ec2_private_key=None, prefix='image', 
                 bucket=None, description=None,
                 kernel_id=None, ramdisk_id=None, 
                 remove_image_files=False, **kwargs):
        self.host = instance # starcluster.node.Node instance
        self.access_key = aws_access_key_id
        self.secret_key = aws_secret_access_key
        self.userid = aws_user_id
        self.private_key = ec2_private_key
        self.bucket = bucket
        self.prefix = prefix
        self.description = description
        self.kernel_id = kernel_id
        self.ramdisk_id = ramdisk_id
        self.cert = ec2_cert
        self.remove_image_files = remove_image_files
        if not utils.is_valid_bucket_name(self.bucket):
            raise exception.InvalidBucketName(self.bucket)
        if not utils.is_valid_image_name(self.prefix):
            raise exception.InvalidImageName(self.prefix)
        self.ec2 = awsutils.EasyEC2(
            aws_access_key_id = self.access_key, 
            aws_secret_access_key = self.secret_key,
        )
        if not self.cert:
            try:
                self.cert = os.environ['EC2_CERT']
            except KeyError,e:
                raise exception.EC2CertRequired()
        if not self.private_key:
            try:
                self.private_key = os.environ['EC2_PRIVATE_KEY']
            except KeyError,e:
                raise exception.EC2PrivateKeyRequired()
        if not os.path.exists(self.cert):
            raise exception.EC2CertDoesNotExist(self.cert)
        if not os.path.exists(self.private_key):
            raise exception.EC2PrivateKeyDoesNotExist(self.private_key)
        self.config_dict = { 
            'access_key': self.access_key, 
            'secret_key': self.secret_key, 
            'private_key': os.path.split(self.private_key)[-1], 
            'userid': self.userid, 
            'cert': os.path.split(self.cert)[-1], 
            'bucket': self.bucket, 
            'prefix': self.prefix,
            'arch': self.host.arch,
        }

    @print_timing
    def create_image(self):
        # first remove any image files from a previous run
        self._remove_image_files()
        self._bundle_image()
        self._upload_image()
        ami_id = self._register_image()
        if self.remove_image_files:
            # remove image files from this run if user says to
            self._remove_image_files()
        return ami_id

    def _remove_image_files(self):
        conn = self.host.ssh
        conn.execute('umount /mnt/img-mnt', ignore_exit_status=True)
        conn.execute('rm -rf /mnt/img-mnt')
        conn.execute('rm -rf /mnt/%(prefix)s*' % self.config_dict)

    def _transfer_pem_files(self):
        """copy pem files to /mnt on image host"""
        conn = self.host.ssh
        conn.put(self.private_key, "/mnt/" + os.path.basename(self.private_key))
        conn.put(self.cert, "/mnt/" + os.path.basename(self.cert))

    @print_timing
    def _bundle_image(self):
        # run script to prepare the host
        conn = self.host.ssh
        config_dict = self.config_dict
        self._transfer_pem_files()
        self.__clean_private_data()
        log.info('Creating the bundled image:')
        conn.execute('ec2-bundle-vol -d /mnt -k /mnt/%(private_key)s \
-c /mnt/%(cert)s -p %(prefix)s -u %(userid)s -r %(arch)s -e /root/.ssh' % \
                     config_dict, 
                     silent=False)
        self._cleanup_pem_files()

    @print_timing
    def _upload_image(self):
        log.info('Uploading bundled image:')
        conn = self.host.ssh
        config_dict = self.config_dict
        conn.execute('ec2-upload-bundle -b %(bucket)s \
-m /mnt/%(prefix)s.manifest.xml -a %(access_key)s -s %(secret_key)s' % \
                     config_dict, silent=False)

    def _cleanup(self):
        #just in case...
        self._cleanup_pem_files()
        conn.execute('rm -f ~/.bash_history', silent=False)

    def _cleanup_pem_files(self):
        log.info('Cleaning up...')
        # delete keys and remove bash history
        conn = self.host.ssh
        conn.execute('rm -f /mnt/*.pem /mnt/*.pem', silent=False)

    def _register_image(self):
        # register image in s3 with ec2
        conn = self.ec2
        config_dict = self.config_dict
        return conn.register_image(
            self.prefix,
            description=self.description,
            image_location= "%(bucket)s/%(prefix)s.manifest.xml" % config_dict,
            kernel_id=self.kernel_id,
            ramdisk_id=self.ramdisk_id,
            architecture=config_dict.get('arch'),
        )

    def __clean_private_data(self):
        log.info('Removing private data...')
        conn = self.host.ssh
        conn.execute('find /home -maxdepth 1 -type d -exec rm -rf {}/.ssh \;',
                     silent=False) 
        conn.execute('rm -f /var/log/secure', silent=False)
        conn.execute('rm -f /var/log/lastlog', silent=False)
        conn.execute('rm -rf /root/*', silent=False)
        conn.execute('rm -f ~/.bash_history', silent=False)
        conn.execute('rm -rf /tmp/*', silent=False)
        conn.execute('rm -rf /root/*.hist*', silent=False)
        conn.execute('rm -rf /var/log/*.gz', silent=False)
