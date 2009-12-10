#!/usr/bin/env python
"""
Module for storing static datastructures
"""

INSTANCE_TYPES = {
    'm1.small':  'i386',
    'm1.large':  'x86_64',
    'm1.xlarge': 'x86_64',
    'c1.medium': 'i386',
    'c1.xlarge': 'x86_64',
    'm2.2xlarge': 'x86_64',
    'm2.4xlarge': 'x86_64',
}

AVAILABLE_SHELLS = [
    "bash", 
    "zsh", 
    "csh", 
    "ksh", 
    "tcsh" 
]

AWS_SETTINGS = {
    # setting, type, required?, default
    'AWS_ACCESS_KEY_ID': (str, True, None),
    'AWS_SECRET_ACCESS_KEY': (str, True, None),
    'AWS_USER_ID': (str, True, None),
}

CLUSTER_SETTINGS = {
    # setting, type, required?, default
    'CLUSTER_SIZE': (int, False, 2),
    'CLUSTER_USER': (str, False, 'sgeadmin'),
    'CLUSTER_SHELL': (str, False, 'bash'),
    'MASTER_IMAGE_ID': (str, False, None),
    'NODE_IMAGE_ID': (str, True, None),
    'INSTANCE_TYPE': (str, True, None),
    'AVAILABILITY_ZONE': (str, False, None),
    # SSH KEYPAIR OPTIONS
    'KEYNAME': (str, True, None),
    'KEY_LOCATION': (str, True, None),
    # EBS OPTIONS
    'ATTACH_VOLUME': (str, False, None),
    'VOLUME_DEVICE': (str, False, None),
    'VOLUME_PARTITION': (str, False, None),
    'EXTENDS': (str, False, None),
}
