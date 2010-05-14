#!/usr/bin/env python
"""
Module for storing static data structures
"""
import os
import tempfile

TMP_DIR = tempfile.gettempdir()
DEBUG_FILE = os.path.join(TMP_DIR, 'starcluster-debug.log')

STARCLUSTER_CFG_DIR = os.path.join(os.path.expanduser('~'),'.starcluster')
STARCLUSTER_CFG_FILE = os.path.join(STARCLUSTER_CFG_DIR, 'config')
STARCLUSTER_PLUGIN_DIR = os.path.join(STARCLUSTER_CFG_DIR, 'plugins')
STARCLUSTER_RECEIPT_DIR = "/var/run/starcluster"
STARCLUSTER_RECEIPT_FILE = os.path.join(STARCLUSTER_RECEIPT_DIR, "receipt.pkl")
STARCLUSTER_OWNER_ID=342652561657

# StarCluster BASE AMIs (i386/x86_64)
BASE_AMI_32="ami-d1c42db8"
BASE_AMI_64="ami-a5c42dcc"

SECURITY_GROUP_PREFIX="@sc"
SECURITY_GROUP_TEMPLATE= '-'.join([SECURITY_GROUP_PREFIX, "%s"])
MASTER_GROUP_NAME="masters"
MASTER_GROUP= SECURITY_GROUP_TEMPLATE % MASTER_GROUP_NAME
MASTER_GROUP_DESCRIPTION="StarCluster Master Nodes"
VOLUME_GROUP_NAME = "volumecreator"
VOLUME_GROUP= SECURITY_GROUP_TEMPLATE % VOLUME_GROUP_NAME
VOLUME_GROUP_DESCRIPTION= "StarCluster createvolume instances"

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

GLOBAL_SETTINGS = {
    'DEFAULT_TEMPLATE': (str, False, None),
    'ENABLE_EXPERIMENTAL': (bool, False, False),
}

AWS_SETTINGS = {
    # setting, type, required?, default
    'AWS_ACCESS_KEY_ID': (str, True, None),
    'AWS_SECRET_ACCESS_KEY': (str, True, None),
    'AWS_USER_ID': (str, False, None),
    'EC2_CERT': (str, False, None),
    'EC2_PRIVATE_KEY': (str, False, None),
    'AWS_PORT': (int, False, None),
    'AWS_EC2_PATH': (str, False, None),
    'AWS_S3_PATH': (str, False, None),
    'AWS_IS_SECURE': (bool, False, None),
    'AWS_REGION_NAME': (str, False, None),
    'AWS_REGION_HOST': (str, False, None),
}

KEY_SETTINGS = {
    'KEY_LOCATION': (str, True, None)
}

EBS_VOLUME_SETTINGS = {
    'VOLUME_ID': (str, True, None),
    'DEVICE': (str, False, None),
    'PARTITION': (int, False, 1),
    'MOUNT_PATH': (str, True, None),
}

PLUGIN_SETTINGS = {
    'SETUP_CLASS': (str, True, None),
}

CLUSTER_SETTINGS = {
    # setting, type, required?, default
    'CLUSTER_SIZE': (int, True, None),
    'CLUSTER_USER': (str, False, 'sgeadmin'),
    'CLUSTER_SHELL': (str, False, 'bash'),
    'MASTER_IMAGE_ID': (str, False, None),
    'MASTER_INSTANCE_TYPE': (str, False, None),
    'NODE_IMAGE_ID': (str, True, None),
    'NODE_INSTANCE_TYPE': (str, True, None),
    'AVAILABILITY_ZONE': (str, False, None),
    # SSH KEYPAIR OPTIONS
    'KEYNAME': (str, True, None),
    'VOLUMES': (str, False, []),
    'EXTENDS': (str, False, None),
    'PLUGINS': (str, False, []),
}
