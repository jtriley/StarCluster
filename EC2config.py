#!/usr/bin/env python
"""
EC2config.py
"""

import sys
import os

#replace these with your AWS keys
AWS_ACCESS_KEY_ID = '0KR8YH6WW79W2CVJBC02'
AWS_SECRET_ACCESS_KEY = 'dLUymDYkF/oXzhJsUMY3cPhoEK5KvLVKd/WcoWrF'

# replace this with your account number
AWS_USERID='342652561657'

#change this to your keypair location (see the EC2 getting started guide tutorial on using ec2-add-keypair)
KEYNAME = "gsg-keypair"
KEY_LOCATION = "/home/jtriley/crypt/amazon/.ec2/id_rsa-gsg-keypair"

#ami for master
MASTER_IMAGE_ID = "ami-3f927556"

#ami for nodes
IMAGE_ID = "ami-3f927556"

# cluster size
DEFAULT_CLUSTER_SIZE = 2 

# create the following user on the cluster
CLUSTER_USER = "sgeadmin"
