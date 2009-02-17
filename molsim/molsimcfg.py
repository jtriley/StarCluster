#!/usr/bin/env python
import os
import sys
import ConfigParser

"""
Reads all variables defined in .molsimcfg config file into molsimcfg module's namespace
"""

if not os.path.exists(os.path.expanduser('~/.molsimcfg')):
    print '>>> please create ~/.molsimcfg...template is below'
    print """
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

# cluster size
DEFAULT_CLUSTER_SIZE = 2

# create the following user on the cluster
CLUSTER_USER = sgeadmin
"""
    sys.exit()

config = ConfigParser.ConfigParser()
config.read(os.path.expanduser('~/.molsimcfg'))

for section in config.sections():
    for option in config.options(section):
        globals()[option.upper()] = config.get(section,option)

DEFAULT_CLUSTER_SIZE=int(DEFAULT_CLUSTER_SIZE)
