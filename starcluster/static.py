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
MASTER_GROUP=SECURITY_GROUP_TEMPLATE % MASTER_GROUP_NAME
MASTER_GROUP_DESCRIPTION="StarCluster Master Nodes"
VOLUME_GROUP_NAME="volumecreator"
VOLUME_GROUP=SECURITY_GROUP_TEMPLATE % VOLUME_GROUP_NAME
VOLUME_GROUP_DESCRIPTION="StarCluster createvolume instances"

IGNORE_GROUPS = [ MASTER_GROUP ]

INSTANCE_TYPES = {
    'm1.small':  'i386',
    'm1.large':  'x86_64',
    'm1.xlarge': 'x86_64',
    'c1.medium': 'i386',
    'c1.xlarge': 'x86_64',
    'm2.2xlarge': 'x86_64',
    'm2.4xlarge': 'x86_64',
}

PROTOCOLS = [
    'tcp','udp','icmp'
]

AVAILABLE_SHELLS = {
    "bash": True, 
    "zsh": True, 
    "csh": True, 
    "ksh": True, 
    "tcsh": True,
}

GLOBAL_SETTINGS = {
    'default_template': (str, False, None),
    'enable_experimental': (bool, False, False),
}

AWS_SETTINGS = {
    # setting, type, required?, default
    'aws_access_key_id': (str, True, None),
    'aws_secret_access_key': (str, True, None),
    'aws_user_id': (str, False, None),
    'ec2_cert': (str, False, None),
    'ec2_private_key': (str, False, None),
    'aws_port': (int, False, None),
    'aws_ec2_path': (str, False, '/'),
    'aws_s3_path': (str, False, '/'),
    'aws_is_secure': (bool, False, True),
    'aws_region_name': (str, False, None),
    'aws_region_host': (str, False, None),
}

KEY_SETTINGS = {
    'key_location': (str, True, None)
}

EBS_VOLUME_SETTINGS = {
    'volume_id': (str, True, None),
    'device': (str, False, None),
    'partition': (int, False, 1),
    'mount_path': (str, True, None),
}

PLUGIN_SETTINGS = {
    'setup_class': (str, True, None),
}

PERMISSION_SETTINGS = {
    # either you're specifying ip-based rule
    'protocol': (str, False, 'tcp'),
    'from_port': (int, False, None),
    'to_port': (int, False, None),
    'cidr_ip': (str, False, '0.0.0.0/0'),
    # or you're allowing full access to another security group
    'source_group': (str, False, None),
    'source_group_owner': (int, False, None),
}

CLUSTER_SETTINGS = {
    # setting, type, required?, default
    'cluster_size': (int, True, None),
    'cluster_user': (str, False, 'sgeadmin'),
    'cluster_shell': (str, False, 'bash'),
    'master_image_id': (str, False, None),
    'master_instance_type': (str, False, None),
    'node_image_id': (str, True, None),
    'node_instance_type': (str, True, None),
    'availability_zone': (str, False, None),
    # SSH KEYPAIR OPTIONS
    'keyname': (str, True, None),
    'extends': (str, False, None),
    'volumes': (list, False, []),
    'plugins': (list, False, []),
    'permissions': (list, False, []),
}
