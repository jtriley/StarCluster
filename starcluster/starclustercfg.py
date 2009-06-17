#!/usr/bin/env python
import os
import sys
import ConfigParser
from ConfigParser import NoOptionError
from templates.config import config_template

"""
Reads all variables defined in .starclustercfg config file into starclustercfg module's namespace
"""

class StarClusterCfg:
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

        if DEFAULT_CLUSTER_SIZE is None:
            print '>>> Required option DEFAULT_CLUSTER_SIZE missing from ~/.starclustercfg'
            sys.exit()
    
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
