#!/usr/bin/env python
"""
Module for storing static datastructures
"""

# StarCluster BASE AMIs (i386/x86_64)
BASE_AMI_32="ami-0330d16a"
BASE_AMI_64="ami-0f30d166"

SECURITY_GROUP_PREFIX="@sc"
MASTER_GROUP="%s-masters" % SECURITY_GROUP_PREFIX
MASTER_GROUP_DESCRIPTION="StarCluster Master Nodes"
SECURITY_GROUP_TEMPLATE=SECURITY_GROUP_PREFIX+"-%s"

INSTANCE_TYPES = {
    'm1.small':  'i386',
    'm1.large':  'x86_64',
    'm1.xlarge': 'x86_64',
    'c1.medium': 'i386',
    'c1.xlarge': 'x86_64',
    'm2.2xlarge': 'x86_64',
    'm2.4xlarge': 'x86_64',
}

AVAILABLE_SHELLS = {
    "bash": True, 
    "zsh": True, 
    "csh": True, 
    "ksh": True, 
    "tcsh": True,
}

AWS_SETTINGS = {
    # setting, type, required?, default
    'AWS_ACCESS_KEY_ID': (str, True, None),
    'AWS_SECRET_ACCESS_KEY': (str, True, None),
    'AWS_USER_ID': (str, True, None),
    'EC2_CERT': (str, False, None),
    'EC2_PRIVATE_KEY': (str, False, None),
}

KEY_SETTINGS = {
    'KEY_LOCATION': (str, True, None)
}

EBS_VOLUME_SETTINGS = {
    'VOLUME_ID': (str, True, None),
    'DEVICE': (str, True, None),
    'PARTITION': (str, True, None),
    'MOUNT_PATH': (str, True, None),
}

CLUSTER_SETTINGS = {
    # setting, type, required?, default
    'CLUSTER_SIZE': (int, True, None),
    'CLUSTER_USER': (str, False, 'sgeadmin'),
    'CLUSTER_SHELL': (str, False, 'bash'),
    'MASTER_IMAGE_ID': (str, False, None),
    'NODE_IMAGE_ID': (str, True, None),
    'INSTANCE_TYPE': (str, True, None),
    'AVAILABILITY_ZONE': (str, False, None),
    # SSH KEYPAIR OPTIONS
    'KEYNAME': (str, True, None),
    'KEY_LOCATION': (str, True, None),
    'VOLUMES': (str, False, None),
    'EXTENDS': (str, False, None),
    'PLUGIN': (str, False, None),
}
