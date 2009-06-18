#!/usr/bin/env python
import os
import sys
import logging
import ConfigParser
from ConfigParser import NoOptionError
from templates.config import config_template

from starcluster import EC2

"""
Reads starcluster configuration settings defined in ~/.starclustercfg config file into starclustercfg module's namespace
"""

log = logging.getLogger('starcluster')


instance_types = {
    'm1.small': True,
    'm1.large': True,
    'm1.xlarge': True,
    'c1.medium': True,
    'c1.xlarge': True,
}

def _get_int(config, section, option):
    try:
        opt = config.getint(section,option)
    except (NoOptionError):
        opt = None
    return opt

def _get_string(config, section, option):
    try:
        opt = config.get(section,option)
    except (NoOptionError):
        opt = None
    return opt

ec2_options = [
    ('AWS_ACCESS_KEY_ID',_get_string, True),
    ('AWS_SECRET_ACCESS_KEY', _get_string, True),
    ('AWS_USERID', _get_string, True),
    ('KEYNAME', _get_string, True),
    ('KEY_LOCATION', _get_string, True),
]

starcluster_options = [
    ('MASTER_IMAGE_ID', _get_string, False),
    ('IMAGE_ID', _get_string, True),
    ('INSTANCE_TYPE', _get_string, False),
    ('AVAILABILITY_ZONE', _get_string, False),
    ('ATTACH_VOLUME', _get_string, False),
    ('VOLUME_DEVICE', _get_string, False),
    ('VOLUME_PARTITION', _get_string, False),
    ('DEFAULT_CLUSTER_SIZE', _get_int, True),
    ('CLUSTER_USER', _get_string, False)
]

sections = [
    ("section ec2", ec2_options),
    ("section starcluster", starcluster_options)
]

def load_settings():
    # TODO: create the template file for them
    if not os.path.exists(os.path.expanduser('~/.starclustercfg')):
        print '>>> It appears this is your first time using StarCluster.'
        print '>>> Please create $HOME/.starclustercfg using the template below:'
        print config_template
        sys.exit(1)

    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser('~/.starclustercfg'))

    for section in sections:
        section_name = section[0]; section_opts = section[1]
        for opt in section_opts:
            name = opt[0]; func = opt[1]; required = opt[2]
            value = func(config,section_name, name)
            globals()[name] = value

def is_valid():
    if not _has_all_required_settings():
        log.error('Please specify the required settings in ~/.starclustercfg')
        return False

    if not _has_valid_credentials():
        log.error('Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination')
        return False

    if not _has_keypair(KEYNAME):
        log.error('Account does not contain a key with KEYNAME = %s. Please check your settings' % KEYNAME)
        return False
    
    if not os.path.exists(KEY_LOCATION):
        log.error('KEY_LOCATION=%s does not exist' % KEY_LOCATION)
        return False

    if not instance_types.has_key(INSTANCE_TYPE):
        log.error("""You specified an invalid INSTANCE_TYPE\nPossible options are:\n%s %s %s %s %s""" % tuple(instance_types.keys()))
        return False
    
    if DEFAULT_CLUSTER_SIZE < 0:
        log.error('>>> DEFAULT_CLUSTER_SIZE must be a positive integer')
        return False
    
    if CLUSTER_USER is None:
        log.warn('>>> No CLUSTER_USER specified. Defaulting to sgeadmin user')
        globals()['CLUSTER_USER'] = 'sgeadmin'

    return True

def _has_all_required_settings():
    has_all_required = True
    for section in sections:
        section_name = section[0]; section_opts = section[1]
        for opt in section_opts:
            name = opt[0]; required = opt[2]
            if required and globals()[name] is None:
                log.warn('Missing setting %s under section "%s"' % (name,section_name))
                has_all_required = False
    return has_all_required

def validate_or_exit():
    if not is_valid():
        log.error('configuration error...exiting')
        sys.exit(1)

def _get_conn():  
    return EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

def _has_valid_credentials():
    conn = _get_conn()
    return not conn.describe_instances().is_error

def _has_keypair(keyname):
    conn = _get_conn()
    keypairs = conn.describe_keypairs().parse()
    has_keypair = False
    for key in keypairs:
        if key[1] == KEYNAME:
            has_keypair = True
    return has_keypair
    
def _load_everything(config):
    for section in config.sections():
        for option in config.options(section):
            globals()[option.upper()] = config.get(section,option)

load_settings()
