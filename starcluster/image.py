#!/usr/bin/env python
import os
import pickle
from optparse import OptionParser
from starcluster import awsutils
from starcluster.logger import log
from starcluster.utils import print_timing

def create_image(cfg):
    pass

class EC2ImageCreator(object):
    def __init__(self, INSTANCE=None, AWS_ACCESS_KEY_ID=None,
                 AWS_SECRET_ACCESS_KEY=None,
                 AWS_USER_ID=None, BUCKET=None, EC2_CERT=None, 
                 EC2_PRIVATE_KEY=None, PREFIX='image', REMOVE_IMAGE_FILES=False):
        self.host = INSTANCE # starcluster.node.Node instance
        self.access_key = AWS_ACCESS_KEY_ID
        self.secret_key = AWS_SECRET_ACCESS_KEY
        self.userid = AWS_USER_ID
        self.bucket = BUCKET
        self.prefix = PREFIX
        self.cert = EC2_CERT
        self.private_key = EC2_PRIVATE_KEY
        self.remove_image_files = REMOVE_IMAGE_FILES
        self.ec2 = awsutils.EasyEC2(
            AWS_ACCESS_KEY_ID = self.access_key, 
            AWS_SECRET_ACCESS_KEY = self.secret_key,
        )
        if not self.cert:
            try:
                self.cert = os.environ['EC2_CERT']
            except KeyError,e:
                log.error('No certificate (pem) file found')
        if not self.private_key:
            try:
                self.private_key = os.environ['EC2_PRIVATE_KEY']
            except KeyError,e:
                log.error('No private key (pem) file found')
        self.config_dict = { 
            'access_key': self.access_key, 
            'secret_key': self.secret_key, 
            'private_key': os.path.split(self.private_key)[-1], 
            'userid': self.userid, 
            'cert': os.path.split(self.cert)[-1], 
            'bucket': self.bucket, 
            'prefix': self.prefix,
            #'arch': self._get_arch(),
            'arch': None,
        }
        if self.host:
            self.config_dict['arch'] = self._get_arch()

    def create_image(self):
        self._bundle_image()
        self._upload_image()
        self._register_image()
        if self.remove_image_files:
            self._remove_image_files()

    def remove_image_files(self):
        conn = self.host.ssh
        conn.execute('rm -rf /mnt/%(prefix)s*' % self.config_dict)

    def _transfer_pem_files(self):
        """copy pem files to /mnt on image host"""
        conn = self.host.ssh
        conn.put(self.private_key, "/mnt/" + os.path.basename(self.private_key))
        conn.put(self.cert, "/mnt/" + os.path.basename(self.cert))

    def _get_arch(self):
        conn = self.host.ssh
        arch = conn.execute(
            'python -c "import platform; print platform.architecture()[0]"'
        )[0]
        if arch == "32bit":
            arch = "i386"
        elif arch == "64bit":
            arch = "x86_64"
        else: 
            arch = "i386"
        return arch

    @print_timing
    def _bundle_image(self):
        # run script to prepare the host
        conn = self.host.ssh
        config_dict = self.config_dict
        self._transfer_pem_files()
        self.__clean_private_data()
        log.info('Creating the bundled image:')
        conn.execute('ec2-bundle-vol -d /mnt -k /mnt/%(private_key)s \
-c /mnt/%(cert)s -p %(prefix)s -u %(userid)s -r %(arch)s' % config_dict, 
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
        conn.execute('rm -f /mnt/pk-*.pem /mnt/cert-*.pem', silent=False)

    def _register_image(self):
        # register image in s3 with ec2
        conn = self.ec2
        config_dict = self.config_dict
        conn.register_image(
            self.prefix,
            image_location= "%(bucket)s/%(prefix)s.manifest.xml" % config_dict,
            architecture=config_dict.get('arch'),
        )

    def __clean_private_data(self):
        log.info('Removing private data...')
        conn = self.host.ssh
        conn.execute('find /home -maxdepth 1 -type d -exec rm -rf {}/.ssh \;',
                     silent=False) 
        conn.execute('rm -rf ~/.ssh/*', silent=False)
        conn.execute('rm -f /var/log/secure', silent=False)
        conn.execute('rm -f /var/log/lastlog', silent=False)
        conn.execute('rm -rf /root/*', silent=False)
        conn.execute('rm -f ~/.bash_history', silent=False)
        conn.execute('rm -rf /tmp/*', silent=False)
        conn.execute('rm -rf /root/*.hist*', silent=False)
        conn.execute('rm -rf /var/log/*.gz', silent=False)

