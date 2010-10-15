#!/usr/bin/env python
"""
Module for storing static data structures
"""
import os
import getpass
import tempfile

TMP_DIR = tempfile.gettempdir()
CURRENT_USER = 'unknown_user'
try:
    CURRENT_USER = getpass.getuser()
except:
    pass
SSH_TEMPLATE = 'ssh -i %s %s@%s'
DEBUG_FILE = os.path.join(TMP_DIR, 'starcluster-debug-%s.log' % CURRENT_USER)

STARCLUSTER_CFG_DIR = os.path.join(os.path.expanduser('~'), '.starcluster')
STARCLUSTER_CFG_FILE = os.path.join(STARCLUSTER_CFG_DIR, 'config')
STARCLUSTER_PLUGIN_DIR = os.path.join(STARCLUSTER_CFG_DIR, 'plugins')
STARCLUSTER_RECEIPT_DIR = "/var/run/starcluster"
STARCLUSTER_RECEIPT_FILE = os.path.join(STARCLUSTER_RECEIPT_DIR, "receipt.pkl")
STARCLUSTER_OWNER_ID = 342652561657

# StarCluster BASE AMIs (i386/x86_64)
BASE_AMI_32 = "ami-d1c42db8"
BASE_AMI_64 = "ami-a5c42dcc"

SECURITY_GROUP_PREFIX = "@sc"
SECURITY_GROUP_TEMPLATE = '-'.join([SECURITY_GROUP_PREFIX, "%s"])
MASTER_GROUP_NAME = "masters"
MASTER_GROUP = SECURITY_GROUP_TEMPLATE % MASTER_GROUP_NAME
MASTER_GROUP_DESCRIPTION = "StarCluster Master Nodes"
VOLUME_GROUP_NAME = "volumecreator"
VOLUME_GROUP = SECURITY_GROUP_TEMPLATE % VOLUME_GROUP_NAME

IGNORE_GROUPS = [MASTER_GROUP]

VOLUME_STATUS = ['creating', 'available', 'in-use',
                 'deleting', 'deleted', 'error']
VOLUME_ATTACH_STATUS = ['attaching', 'attached', 'detaching', 'detached']

INSTANCE_TYPES = {
    'm1.small': 'i386',
    'm1.large': 'x86_64',
    'm1.xlarge': 'x86_64',
    'c1.medium': 'i386',
    'c1.xlarge': 'x86_64',
    'm2.xlarge': 'x86_64',
    'm2.2xlarge': 'x86_64',
    'm2.4xlarge': 'x86_64',
    'cc1.4xlarge': 'x86_64',
}

CLUSTER_COMPUTE_TYPES = ['cc1.4xlarge']

SPOT_TYPES = [t for t in INSTANCE_TYPES if t not in CLUSTER_COMPUTE_TYPES]

PROTOCOLS = ['tcp', 'udp', 'icmp']

AVAILABLE_SHELLS = {
    "bash": True,
    "zsh": True,
    "csh": True,
    "ksh": True,
    "tcsh": True,
}

GLOBAL_SETTINGS = {
    # setting, type, required?, default, options
    'default_template': (str, False, None, None),
    'enable_experimental': (bool, False, False, None),
}

AWS_SETTINGS = {
    'aws_access_key_id': (str, True, None, None),
    'aws_secret_access_key': (str, True, None, None),
    'aws_user_id': (str, False, None, None),
    'ec2_cert': (str, False, None, None),
    'ec2_private_key': (str, False, None, None),
    'aws_port': (int, False, None, None),
    'aws_ec2_path': (str, False, '/', None),
    'aws_s3_path': (str, False, '/', None),
    'aws_is_secure': (bool, False, True, None),
    'aws_region_name': (str, False, None, None),
    'aws_region_host': (str, False, None, None),
    'aws_s3_host': (str, False, None, None),
}

KEY_SETTINGS = {
    'key_location': (str, True, None, None),
}

EBS_VOLUME_SETTINGS = {
    'volume_id': (str, True, None, None),
    'device': (str, False, None, None),
    'partition': (int, False, 1, None),
    'mount_path': (str, True, None, None),
}

PLUGIN_SETTINGS = {
    'setup_class': (str, True, None, None),
}

PERMISSION_SETTINGS = {
    # either you're specifying an ip-based rule
    'ip_protocol': (str, False, 'tcp', PROTOCOLS),
    'from_port': (int, True, None, None),
    'to_port': (int, True, None, None),
    'cidr_ip': (str, False, '0.0.0.0/0', None),
    # or you're allowing full access to another security group
    # skip this for now...these two options are mutually exclusive to
    # the four settings above and source_group is  less commonly
    # used. address this when someone requests it.
    #'source_group': (str, False, None),
    #'source_group_owner': (int, False, None),
}

CLUSTER_SETTINGS = {
    'cluster_size': (int, True, None, None),
    'cluster_user': (str, False, 'sgeadmin', None),
    'cluster_shell': (str, False, 'bash', AVAILABLE_SHELLS.keys()),
    'master_image_id': (str, False, None, None),
    'master_instance_type': (str, False, None, INSTANCE_TYPES.keys()),
    'node_image_id': (str, True, None, None),
    'node_instance_type': (list, True, [], None),
    'availability_zone': (str, False, None, None),
    'keyname': (str, True, None, None),
    'extends': (str, False, None, None),
    'volumes': (list, False, [], None),
    'plugins': (list, False, [], None),
    'permissions': (list, False, [], None),
}
