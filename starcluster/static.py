#!/usr/bin/env python
"""
Module for storing static data structures
"""
import os
import getpass
import tempfile

PID = os.getpid()
TMP_DIR = tempfile.gettempdir()
if os.path.exists("/tmp"):
    TMP_DIR = "/tmp"
CURRENT_USER = 'unknown_user'
try:
    CURRENT_USER = getpass.getuser()
except:
    pass
SSH_TEMPLATE = 'ssh -i %s %s@%s'
DEBUG_FILE = os.path.join(TMP_DIR, 'starcluster-debug-%s.log' % CURRENT_USER)
SSH_DEBUG_FILE = os.path.join(TMP_DIR, 'starcluster-ssh-%s.log' % CURRENT_USER)
AWS_DEBUG_FILE = os.path.join(TMP_DIR, 'starcluster-aws-%s.log' % CURRENT_USER)

STARCLUSTER_CFG_DIR = os.path.join(os.path.expanduser('~'), '.starcluster')
STARCLUSTER_CFG_FILE = os.path.join(STARCLUSTER_CFG_DIR, 'config')
STARCLUSTER_PLUGIN_DIR = os.path.join(STARCLUSTER_CFG_DIR, 'plugins')
STARCLUSTER_RECEIPT_DIR = "/var/run/starcluster"
STARCLUSTER_RECEIPT_FILE = os.path.join(STARCLUSTER_RECEIPT_DIR, "receipt.pkl")
STARCLUSTER_OWNER_ID = 342652561657

# StarCluster BASE AMIs (i386/x86_64)
BASE_AMI_32 = "ami-8cf913e5"
BASE_AMI_64 = "ami-0af31963"

SECURITY_GROUP_PREFIX = "@sc"
SECURITY_GROUP_TEMPLATE = '-'.join([SECURITY_GROUP_PREFIX, "%s"])
MASTER_GROUP_NAME = "masters"
MASTER_GROUP = SECURITY_GROUP_TEMPLATE % MASTER_GROUP_NAME
MASTER_GROUP_DESCRIPTION = "StarCluster Master Nodes"
VOLUME_GROUP_NAME = "volumecreator"
VOLUME_GROUP = SECURITY_GROUP_TEMPLATE % VOLUME_GROUP_NAME

IGNORE_GROUPS = [MASTER_GROUP]

INSTANCE_STATES = ['pending', 'running', 'shutting-down',
                   'terminated', 'stopping', 'stopped']

VOLUME_STATUS = ['creating', 'available', 'in-use',
                 'deleting', 'deleted', 'error']
VOLUME_ATTACH_STATUS = ['attaching', 'attached', 'detaching', 'detached']

INSTANCE_TYPES = {
    't1.micro': ['i386', 'x86_64'],
    'm1.small': ['i386'],
    'm1.large': ['x86_64'],
    'm1.xlarge': ['x86_64'],
    'c1.medium': ['i386'],
    'c1.xlarge': ['x86_64'],
    'm2.xlarge': ['x86_64'],
    'm2.2xlarge': ['x86_64'],
    'm2.4xlarge': ['x86_64'],
    'cc1.4xlarge': ['x86_64'],
    'cg1.4xlarge': ['x86_64'],
}

MICRO_INSTANCE_TYPES = ['t1.micro']

CLUSTER_COMPUTE_TYPES = ['cc1.4xlarge']

CLUSTER_GPU_TYPES = ['cg1.4xlarge']

CLUSTER_TYPES = CLUSTER_COMPUTE_TYPES + CLUSTER_GPU_TYPES

SPOT_TYPES = [t for t in INSTANCE_TYPES if t not in CLUSTER_TYPES]

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
    'refresh_interval': (int, False, 30, None),
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
    'partition': (int, False, None, None),
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
    'disable_queue': (bool, False, False, None),
}
