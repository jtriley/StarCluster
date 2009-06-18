#!/usr/bin/env python
import os
import sys
import logging
import ConfigParser
from ConfigParser import NoOptionError
from templates.config import config_template

from starcluster import EC2

"""
Reads all variables defined in .starclustercfg config file into starclustercfg module's namespace
"""

log = logging.getLogger('starcluster')

class StarClusterCfg:
    instance_types = {
        'm1.small': True,
        'm1.large': True,
        'm1.xlarge': True,
        'c1.medium': True,
        'c1.xlarge': True,
    }

    def __init__(self):
        # TODO: Make this better still...this at least gets the job done for now
        if not os.path.exists(os.path.expanduser('~/.starclustercfg')):
            print '>>> please create ~/.starclustercfg...template is below'
            print config_template
            sys.exit(1)

        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.expanduser('~/.starclustercfg'))

        ec2_options = [
            ('AWS_ACCESS_KEY_ID',self.get_string),
            ('AWS_SECRET_ACCESS_KEY', self.get_string),
            ('AWS_USERID', self.get_string),
            ('KEYNAME', self.get_string),
            ('KEY_LOCATION', self.get_string),
        ]

        starcluster_options = [
            ('MASTER_IMAGE_ID', self.get_string),
            ('IMAGE_ID', self.get_string),
            ('INSTANCE_TYPE', self.get_string),
            ('AVAILABILITY_ZONE', self.get_string),
            ('ATTACH_VOLUME', self.get_string),
            ('VOLUME_DEVICE', self.get_string),
            ('VOLUME_PARTITION', self.get_string),
            ('DEFAULT_CLUSTER_SIZE', self.get_int),
            ('CLUSTER_USER', self.get_string)
        ]

        section = "section ec2"
        for opt in ec2_options:
            globals()[opt[0]] = opt[1](section, opt[0])

        section = "section starcluster"
        for opt in starcluster_options:
            globals()[opt[0]] = opt[1](section, opt[0])

        if not self.validate():
            log.error('configuration error...exiting')
            sys.exit(1)

    def validate(self):
        #todo check for network connectivity
        conn = EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        error = conn.describe_instances().is_error
        if error:
            log.error('>>> Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination')
            return False
    
        keypairs = conn.describe_keypairs().parse()
        has_keyname = False
        for key in keypairs:
            if key[1] == KEYNAME:
                has_keyname = True

        if not has_keyname:
            log.error('>>> KEYNAME = %s not found' % KEYNAME)
            return False
        
        if not os.path.exists(KEY_LOCATION):
            log.error('>>> KEY_LOCATION=%s does not exist' % KEY_LOCATION)
            return False

        if IMAGE_ID is None:
            log.error('You did not specify IMAGE_ID')
            return False

        if not self.instance_types.has_key(INSTANCE_TYPE):
            log.error('Missing or invalid INSTANCE_TYPE')
            return False
        
        if DEFAULT_CLUSTER_SIZE is None:
            log.error('>>> Required option DEFAULT_CLUSTER_SIZE missing from ~/.starclustercfg')
            return False

        if DEFAULT_CLUSTER_SIZE < 0:
            log.error('>>> DEFAULT_CLUSTER_SIZE must be a positive integer')
            return False
        
        if CLUSTER_USER is None:
            log.warn('>>> No CLUSTER_USER specified. Defaulting to sgeadmin user')
            globals()['CLUSTER_USER'] = 'sgeadmin'

        return True
        
        
    def load_everything(self):
        for section in self.config.sections():
            for option in self.config.options(section):
                globals()[option.upper()] = self.config.get(section,option)

    def get_int(self, section,option):
        try:
            opt = self.config.getint(section,option)
        except (NoOptionError):
            opt = None
        return opt

    def get_string(self, section, option):
        try:
            opt = self.config.get(section,option)
        except (NoOptionError):
            opt = None
        return opt

StarClusterCfg()
