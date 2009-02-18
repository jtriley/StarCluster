#!/usr/bin/env python
import os
import sys
import ConfigParser
from ConfigParser import NoOptionError

"""
Reads all variables defined in .molsimcfg config file into molsimcfg module's namespace
"""

class MolsimCfg:
    config_template = """
[section ec2]
#replace these with your AWS keys
AWS_ACCESS_KEY_ID = #your_aws_access_key_id
AWS_SECRET_ACCESS_KEY = #your_secret_access_key

# replace this with your account number
AWS_USERID= #your userid

# change this to your keypair location 
# (see the EC2 getting started guide tutorial on using ec2-add-keypair)
KEYNAME = #your keypair name
KEY_LOCATION = #/path/to/your/keypair

[section molsim]
# ami for master
MASTER_IMAGE_ID = ami-00000000

# ami for nodes
IMAGE_ID = ami-11111111

# instance type
INSTANCE_TYPE = m1.small

# availability zone
AVAILABILITY_ZONE = us-east-1c

# attach volume to /home on master node
ATTACH_VOLUME = vol-abcdefgh
VOLUME_DEVICE = /dev/sdd
VOLUME_PARTITION = /dev/sdd1

# cluster size
DEFAULT_CLUSTER_SIZE = 2

# create the following user on the cluster
CLUSTER_USER = sgeadmin
    """
    def __init__(self):
        # TODO: Make this better still...this at least gets the job done for now
        if not os.path.exists(os.path.expanduser('~/.molsimcfg')):
            print '>>> please create ~/.molsimcfg...template is below'
            print self.config_template
            sys.exit()

        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.expanduser('~/.molsimcfg'))

        ec2_options = [
            ('AWS_ACCESS_KEY_ID',self.get_string),
            ('AWS_SECRET_ACCESS_KEY', self.get_string),
            ('AWS_USERID', self.get_string),
            ('KEYNAME', self.get_string),
            ('KEY_LOCATION', self.get_string),
        ]

        molsim_options = [
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

        section = "section molsim"
        for opt in molsim_options:
            globals()[opt[0]] = opt[1](section, opt[0])

        if DEFAULT_CLUSTER_SIZE is None:
            print '>>> Required option DEFAULT_CLUSTER_SIZE missing from ~/.molsimcfg'
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

MolsimCfg()
