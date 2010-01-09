#!/usr/bin/env python
import os
import pickle
from optparse import OptionParser

from starcluster import EC2
from starcluster.starclustercfg import *
from starcluster.ssh import Connection

class EC2ImageCreator(object):
    def __init__(self, AWS_ACCESS_KEY_ID=None, AWS_SECRET_ACCESS_KEY=None,
                 AWS_USER_ID=None, BUCKET=None, EC2_CERT=None, 
                 EC2_PRIVATE_KEY=None, PREFIX='image'):
        self.host = host
        self.access_key = AWS_ACCESS_KEY_ID
        self.secret_key = AWS_SECRET_ACCESS_KEY
        self.userid = AWS_USER_ID
        self.bucket = BUCKET
        self.prefix = PREFIX
        self.cert = EC2_CERT
        self.private_key = EC2_PRIVATE_KEY
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

    def create_image(self):
        self._transfer_pem_files()
        self._bundle_and_register()

    def _transfer_pem_files(self):
        """copy pem files to /mnt on image host"""
        conn = self.host.ssh
        conn.put(self.private_key, "/mnt/" + os.path.basename(EC2_PRIVATE_KEY))
        conn.put(self.cert, "/mnt/" + os.path.basename(EC2_CERT))

    def _bundle_and_register(self):
        # run script to prepare the host
        conn = self.host.ssh
        config_dict = {
            'private_key': self.private_key,
            'cert': self.cert,
            'userid': self.userid,
            'prefix': self.prefix,
            'bucket': self.bucket,
            'access_key': self.access_key,
            'secret_key': self.secret_key,
        }
        log.info('Removing private data...')
        conn.execute('find /home -maxdepth 1 -type d -exec rm -rf {}/.ssh \;',
                     silent=False) 
        conn.execute('rm -rf ~/.ssh/*', silent=False)
        conn.execute('rm -f /var/log/secure', silent=False)
        conn.execute('rm -f /var/log/lastlog', silent=False)
        conn.execute('rm -rf /root/*', silent=False)
        conn.execute('rm -f ~/.bash_history', silent=False)
        conn.execute('rm -rf /tmp/*', silent=False)
        arch = myssh.execute(
            'python -c "import platform; print platform.architecture()[0]"'
        )[0]
        if arch == "32bit":
            arch = "i386"
        elif arch == "64bit":
            arch = "x86_64"
        else: 
            arch = "i386"
        config_dict['arch'] = arch

        log.info('Creating the bundled image:')
        conn.execute('ec2-bundle-vol -d /mnt -k /mnt/%(private_key)s \
-c /mnt/%(cert)s -p %(prefix)s -u %(userid)s -r %(arch)s' % config_dict, 
                     silent=False)

        log.info('Uploading the bundled image:')
        conn.execute('ec2-upload-bundle -b %(bucket)s \
-m /mnt/%(prefix)s.manifest.xml -a %(access_key)s -s %(secret_key)s' % \
                     config_dict, silent=False)

        log.info('Cleaning up...')
        # delete keys and remove bash history
        conn.execute('rm -f /mnt/pk-*.pem /mnt/cert-*.pem', silent=False)
        conn.execute('rm -f ~/.bash_history', silent=False)

        # register compute node image we just created
        self.conn.register_image(
            "%(bucket)s/%(prefix)s.manifest.xml" % self.config_dict
        )
