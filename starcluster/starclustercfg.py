#!/usr/bin/env python
import os
import sys
import logging
import ConfigParser
from templates.config import config_template

from starcluster import EC2

"""
Reads starcluster configuration settings defined in ~/.starclustercfg config file into starclustercfg module's namespace
"""

log = logging.getLogger('starcluster')

CFG_FILE = os.path.join(os.path.expanduser('~'),'.starclustercfg')

instance_types = {
    'm1.small':  'i386',
    'm1.large':  'x86_64',
    'm1.xlarge': 'x86_64',
    'c1.medium': 'i386',
    'c1.xlarge': 'x86_64',
}

def _get_int(config, section, option):
    try:
        opt = config.getint(section,option)
    except (ConfigParser.NoSectionError):
        opt = None
    except (ConfigParser.NoOptionError):
        opt = None
    return opt

def _get_string(config, section, option):
    try:
        opt = config.get(section,option)
    except (ConfigParser.NoSectionError):
        opt = None
    except (ConfigParser.NoOptionError):
        opt = None
    return opt

# setting, type, required?, default
aws_options = [
    ('AWS_ACCESS_KEY_ID', _get_string, True, None),
    ('AWS_SECRET_ACCESS_KEY', _get_string, True, None),
    ('AWS_USER_ID', _get_string, True, None),
]

ssh_options = [
    ('KEYNAME', _get_string, True, None),
    ('KEY_LOCATION', _get_string, True, None),
]

cluster_options = [
    ('DEFAULT_CLUSTER_SIZE', _get_int, False, 2),
    ('CLUSTER_USER', _get_string, False, 'sgeadmin'),
    ('CLUSTER_SHELL', _get_string, False, 'bash'),
    ('MASTER_IMAGE_ID', _get_string, False, None),
    ('NODE_IMAGE_ID', _get_string, True, None),
    ('INSTANCE_TYPE', _get_string, True, None),
    ('AVAILABILITY_ZONE', _get_string, False, None),
]

ebs_options = [
    ('ATTACH_VOLUME', _get_string, False, None),
    ('VOLUME_DEVICE', _get_string, False, None),
    ('VOLUME_PARTITION', _get_string, False, None),
]

sections = [
    ("section aws", aws_options),
    ("section ssh", ssh_options),
    ("section cluster", cluster_options),
    ("section ebs", ebs_options),
]

def load_settings():
    # TODO: create the template file for them?
    if not os.path.exists(CFG_FILE):
        log.info('It appears this is your first time using StarCluster.')
        log.info('Please create %s using the template below:' % CFG_FILE)
        print config_template
        sys.exit(1)

    config = ConfigParser.ConfigParser()
    try:
        config.read(CFG_FILE)
    except ConfigParser.MissingSectionHeaderError,e:
        log.warn('No sections defined in settings file %s' % CFG_FILE)
        pass

    for section in sections:
        section_name = section[0]; section_opts = section[1]
        for opt in section_opts:
            name = opt[0]; func = opt[1]; required = opt[2]; default = opt[3]
            value = func(config,section_name, name)
            if value is None and default is not None:
                log.warn('No %s setting specified. Defaulting to %s' % (name, default))
                globals()[name] = default
            else:
                globals()[name] = value

def is_valid():
    conn = _get_conn()

    if not _has_all_required_settings():
        log.error('Please specify the required settings in %s' % CFG_FILE)
        return False

    if not _has_valid_credentials(conn):
        log.error('Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination. Please check your settings')
        return False

    if not _has_keypair(conn):
        log.error('Account does not contain a key with KEYNAME = %s. Please check your settings' % KEYNAME)
        return False
    
    if not os.path.exists(KEY_LOCATION):
        log.error('KEY_LOCATION=%s does not exist. Please check your settings' % KEY_LOCATION)
        return False
    elif not os.path.isfile(KEY_LOCATION):
        log.error('KEY_LOCATION=%s is not a file. Please check your settings' % KEY_LOCATION)
        return False
    
    if DEFAULT_CLUSTER_SIZE <= 0:
        log.error('DEFAULT_CLUSTER_SIZE must be a positive integer. Please check your settings')
        return False
    
    if not _has_valid_availability_zone(conn):
        log.error('Your AVAILABILITY_ZONE setting is invalid. Please check your settings')
        return False

    if not _has_valid_ebs_settings(conn):
        log.error('EBS settings are invalid. Please check your settings')
        return False

    if not _has_valid_image_settings(conn):
        log.error('Your MASTER_IMAGE_ID/NODE_IMAGE_ID setting(s) are invalid. Please check your settings')
        return False

    if not _has_valid_instance_type_settings(conn):
        log.error('Your INSTANCE_TYPE setting is invalid. Please check your settings')
        return False


    return True

def _has_valid_image_settings(conn):
    image = conn.describe_images(imageIds=[NODE_IMAGE_ID]).parse()
    if not image:
        log.error('NODE_IMAGE_ID %s does not exist' % NODE_IMAGE_ID)
        return False
    if MASTER_IMAGE_ID is not None:
        master_image = conn.describe_images(imageIds=[MASTER_IMAGE_ID]).parse()
        if not master_image:
            log.error('MASTER_IMAGE_ID %s does not exist' % MASTER_IMAGE_ID)
            return False
    return True

def _has_valid_availability_zone(conn):
    if AVAILABILITY_ZONE is not None:
        zone_list = conn.describe_availability_zones().parse()
        if not zone_list:
            log.error('No availability zones found')
            return False

        zones = {}
        for zone in zone_list:
            zones[zone[1]] = zone[2]

        if not zones.has_key(AVAILABILITY_ZONE):
            log.error('AVAILABILITY_ZONE = %s does not exist' % AVAILABILITY_ZONE)
            return False
        elif zones[AVAILABILITY_ZONE] != 'available':
            log.error('The AVAILABILITY_ZONE = %s is not available at this time')
            return False
    return True

def _has_valid_instance_type_settings(conn):
    if not instance_types.has_key(INSTANCE_TYPE):
        log.error("""You specified an invalid INSTANCE_TYPE\nPossible options are:\n%s %s %s %s %s""" % tuple(instance_types.keys()))
        return False

    node_image_platform = conn.describe_images(imageIds=[NODE_IMAGE_ID]).parse()[0][6]
    instance_platform = instance_types[INSTANCE_TYPE]
    if instance_platform != node_image_platform:
        log.error('You specified an incompatible NODE_IMAGE_ID and INSTANCE_TYPE')
        log.error('INSTANCE_TYPE = %(instance_type)s is for a %(instance_platform)s \
platform while NODE_IMAGE_ID = %(node_image_id)s is a %(node_image_platform)s platform' \
                    % { 'instance_type': INSTANCE_TYPE, 'instance_platform': instance_platform, \
                        'node_image_id': NODE_IMAGE_ID, 'node_image_platform': node_image_platform})
        return False
    
    if MASTER_IMAGE_ID is not None:
        master_image_platform = conn.describe_images(imageIds=[MASTER_IMAGE_ID]).parse()[0][6]
        if instance_platform != master_image_platform:
            log.error('You specified an incompatible MASTER_IMAGE_ID and INSTANCE_TYPE')
            log.error('INSTANCE_TYPE = %(instance_type)s is for a %(instance_platform)s \
platform while MASTER_IMAGE_ID = %(master_image_id)s is a %(master_image_platform)s platform' \
                        % { 'instance_type': INSTANCE_TYPE, 'instance_platform': instance_platform, \
                            'image_id': MASETER_IMAGE_ID, 'master_image_platform': master_image_platform})
            return False
    
    return True

def _has_valid_ebs_settings(conn):
    #TODO check that ATTACH_VOLUME id exists
    if ATTACH_VOLUME is not None:
        vol = conn.describe_volumes(volumeIds=[ATTACH_VOLUME]).parse()
        if not vol:
            log.error('ATTACH_VOLUME = %s does not exist' % ATTACH_VOLUME)
            return False
        vol = vol[0]
        if VOLUME_DEVICE is None:
            log.error('Must specify VOLUME_DEVICE when specifying ATTACH_VOLUME setting')
            return False
        if VOLUME_PARTITION is None:
            log.error('Must specify VOLUME_PARTITION when specifying ATTACH_VOLUME setting')
            return False
        if AVAILABILITY_ZONE is not None:
            vol_zone = vol[3]
            if vol.count(AVAILABILITY_ZONE) == 0:
                log.error('The ATTACH_VOLUME you specified is only available in zone %(vol_zone)s, \
however, you specified AVAILABILITY_ZONE = %(availability_zone)s\nYou need to \
either change AVAILABILITY_ZONE or create a new volume in %(availability_zone)s' \
                            % {'vol_zone': vol_zone, 'availability_zone': AVAILABILITY_ZONE})
                return False
    return True

def _has_all_required_settings():
    has_all_required = True
    for section in sections:
        section_name = section[0]; section_opts = section[1]
        for opt in section_opts:
            name = opt[0]; required = opt[2]; default=opt[3]
            if required and globals()[name] is None:
                log.warn('Missing required setting %s under section [%s]' % (name,section_name))
                has_all_required = False
    return has_all_required

def validate_aws_or_exit():
    conn = _get_conn()
    if conn is None or not _has_valid_credentials(conn):
        log.error('Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination. Please check your settings')
        sys.exit(1)
    
def validate_or_exit():
    if not is_valid():
        log.error('configuration error...exiting')
        sys.exit(1)

def _get_conn():  
    if AWS_ACCESS_KEY_ID is None or AWS_SECRET_ACCESS_KEY is None:
        return None
    return EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

def _has_valid_credentials(conn):
    return not conn.describe_instances().is_error

def _has_keypair(conn):
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
