#!/usr/bin/env python
import os
import sys
import ConfigParser
from templates.config import config_template

from starcluster import EC2
from starcluster.logger import log

class InvalidOptions(Exception):
    pass

class ClusterDoesNotExist(Exception):
    pass

class AttributeDict(dict):
    """ Subclass of dict that allows read-only attribute-like access to
    dictionary key/values"""
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError,e:
            return super(StarClusterConfig, self).__getattribute__(name)

class StarClusterConfig(AttributeDict):
    """
    Loads StarCluster configuration settings defined in ~/.starclustercfg config file
    Settings are available as follows:

    cfg = StarClusterConfig()
    cfg.load()
    aws_info = cfg.aws_info
    cluster_cfg = cfg.mycluster
    print cluster_cfg
    """

    CFG_FILE = os.path.join(os.path.expanduser('~'),'.starclustercfg')

    # until i can find a way to query AWS for these...
    instance_types = {
        'm1.small':  'i386',
        'm1.large':  'x86_64',
        'm1.xlarge': 'x86_64',
        'c1.medium': 'i386',
        'c1.xlarge': 'x86_64',
        'm2.2xlarge': 'x86_64',
        'm2.4xlarge': 'x86_64',
    }

    def __init__(self):
        # setting, type, required?, default
        self.aws_settings = [
            ('AWS_ACCESS_KEY_ID', self._get_string, True, None),
            ('AWS_SECRET_ACCESS_KEY', self._get_string, True, None),
            ('AWS_USER_ID', self._get_string, True, None),
        ]

        self.cluster_settings = [
            ('CLUSTER_SIZE', self._get_int, False, 2),
            ('CLUSTER_USER', self._get_string, False, 'sgeadmin'),
            ('CLUSTER_SHELL', self._get_string, False, 'bash'),
            ('MASTER_IMAGE_ID', self._get_string, False, None),
            ('NODE_IMAGE_ID', self._get_string, True, None),
            ('INSTANCE_TYPE', self._get_string, True, None),
            ('AVAILABILITY_ZONE', self._get_string, False, None),
            # SSH KEYPAIR OPTIONS
            ('KEYNAME', self._get_string, True, None),
            ('KEY_LOCATION', self._get_string, True, None),
            # EBS OPTIONS
            ('ATTACH_VOLUME', self._get_string, False, None),
            ('VOLUME_DEVICE', self._get_string, False, None),
            ('VOLUME_PARTITION', self._get_string, False, None),
            ('EXTENDS', self._get_string, False, None),
        ]

        self._config = None
        self._conn = None
        self.aws_section = "aws info"
        self.cluster_sections = []

    def _get_int(self, config, section, option):
        try:
            opt = config.getint(section,option)
        except (ConfigParser.NoSectionError):
            opt = None
        except (ConfigParser.NoOptionError):
            opt = None
        except (ValueError):
            log.warn("Expected integer value for option %s in %s, not setting option!" % (option,section))
            opt = None
        return opt

    def _get_string(self, config, section, option):
        try:
            opt = config.get(section,option)
        except (ConfigParser.NoSectionError):
            opt = None
        except (ConfigParser.NoOptionError):
            opt = None
        return opt

    @property
    def conn(self):  
        if self._conn is None:
            if self.aws.AWS_ACCESS_KEY_ID is None or self.aws.AWS_SECRET_ACCESS_KEY is None:
                return None
            else:
                self._conn = EC2.AWSAuthConnection(self.aws.AWS_ACCESS_KEY_ID, self.aws.AWS_SECRET_ACCESS_KEY)
        return self._conn

    @property
    def config(self):
        # TODO: create the template file for them?
        CFG_FILE = self.CFG_FILE
        if not os.path.exists(CFG_FILE):
            print config_template
            log.info('It appears this is your first time using StarCluster.')
            log.info('Please create %s using the template above.' % CFG_FILE)
            sys.exit(1)
        if self._config is None:
            try:
                self._config = ConfigParser.ConfigParser()
                self._config.read(CFG_FILE)
            except ConfigParser.MissingSectionHeaderError,e:
                log.warn('No sections defined in settings file %s' % CFG_FILE)
        return self._config

    def load_settings(self, section_name, settings, section_key=None):
        if section_key is None:
            section_key = section_name
        section_conf = self.get(section_key)
        if not section_conf:
            self[section_key] = AttributeDict()
            section_conf = self[section_key]
        for opt in settings:
            name = opt[0]; func = opt[1]; required = opt[2]; default = opt[3]
            value = func(self.config, section_name, name)
            if value is not None:
                section_conf[name] = value

    def load_defaults(self, section_key, settings):
        section_conf = self.get(section_key, None)
        if not section_conf:
            section_conf = self[section_key] = AttributeDict()
        for opt in settings:
            name = opt[0]; default = opt[3]
            if section_conf.get(name, None) is None:
                if default is not None:
                    log.warn('No %s setting specified. Defaulting to %s' % (name, default))
                section_conf[name] = default

    def load_extends_variables(self, section_key):
        cluster_section = self[section_key]
        cluster_extends = cluster_section['EXTENDS'] = cluster_section.get('EXTENDS', None)
        if cluster_extends is None:
            return
        log.debug('%s extends %s' % (section_key, cluster_extends))
        cluster_extensions = [cluster_section]
        while True:
            extends = cluster_section.get('EXTENDS',None)
            if extends:
                try:
                    cluster_section = self[extends]
                    cluster_extensions.insert(0, cluster_section)
                except KeyError,e:
                    log.warn("can't extend non-existent section %s" % extends)
                    break
            else:
                break
        transform = AttributeDict()
        for extension in cluster_extensions:
            transform.update(extension)
        self[section_key] = transform

    def load(self):
        self.load_settings(self.aws_section, self.aws_settings, 'aws')
        self.cluster_sections = [section for section in self.config.sections() if section.startswith('cluster')]
        self.clusters = [ section.split()[1] for section in self.cluster_sections ]
        for section in self.cluster_sections:
            section_label = section.split()[1]
            self.load_settings(section, self.cluster_settings, section_label)
        for section in self.cluster_sections:
            section_label = section.split()[1]
            self.load_extends_variables(section_label)
            self.load_defaults(section_label, self.cluster_settings)


    def is_valid(self, cluster): 
        CLUSTER_SIZE = cluster.CLUSTER_SIZE
        KEYNAME = cluster.KEYNAME
        KEY_LOCATION = cluster.KEY_LOCATION
        conn = self.conn 
        if not self._has_all_required_settings(cluster):
            log.error('Please specify the required settings in %s' % CFG_FILE)
            return False
        if not self._has_valid_credentials():
            log.error('Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination. Please check your settings')
            return False
        if not self._has_keypair(cluster):
            log.error('Account does not contain a key with KEYNAME = %s. Please check your settings' % KEYNAME)
            return False
        if not os.path.exists(KEY_LOCATION):
            log.error('KEY_LOCATION=%s does not exist. Please check your settings' % KEY_LOCATION)
            return False
        elif not os.path.isfile(KEY_LOCATION):
            log.error('KEY_LOCATION=%s is not a file. Please check your settings' % KEY_LOCATION)
            return False
        if CLUSTER_SIZE <= 0:
            log.error('CLUSTER_SIZE must be a positive integer. Please check your settings')
            return False
        if not self._has_valid_availability_zone(cluster):
            log.error('Your AVAILABILITY_ZONE setting is invalid. Please check your settings')
            return False
        if not self._has_valid_ebs_settings(cluster):
            log.error('EBS settings are invalid. Please check your settings')
            return False
        if not self._has_valid_image_settings(cluster):
            log.error('Your MASTER_IMAGE_ID/NODE_IMAGE_ID setting(s) are invalid. Please check your settings')
            return False
        if not self._has_valid_instance_type_settings(cluster):
            log.error('Your INSTANCE_TYPE setting is invalid. Please check your settings')
            return False
        return True

    def get_cluster(self, cluster_name):
        try:
            return self[cluster_name]
        except KeyError,e:
            raise ClusterDoesNotExist('config for cluster %s does not exist' % cluster_name)

    def get_clusters(self):
        clusters = []
        for section in self.cluster_sections:
            clusters.append(section.replace('cluster ','',1).strip())
        return clusters

    def _has_valid_image_settings(self, cluster):
        MASTER_IMAGE_ID = cluster.MASTER_IMAGE_ID
        NODE_IMAGE_ID = cluster.NODE_IMAGE_ID
        conn = self.conn
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

    def _has_valid_availability_zone(self, cluster):
        conn = self.conn
        AVAILABILITY_ZONE = cluster.AVAILABILITY_ZONE
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

    def _has_valid_instance_type_settings(self, cluster):
        MASTER_IMAGE_ID = cluster.MASTER_IMAGE_ID
        NODE_IMAGE_ID = cluster.NODE_IMAGE_ID
        INSTANCE_TYPE = cluster.INSTANCE_TYPE
        instance_types = self.instance_types
        conn = self.conn
        if not instance_types.has_key(INSTANCE_TYPE):
            log.error("You specified an invalid INSTANCE_TYPE %s \nPossible options are:\n%s" % (INSTANCE_TYPE,' '.join(instance_types.keys())))
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

    def _has_valid_ebs_settings(self, cluster):
        #TODO check that ATTACH_VOLUME id exists
        ATTACH_VOLUME = cluster.ATTACH_VOLUME
        VOLUME_DEVICE = cluster.VOLUME_DEVICE
        VOLUME_PARTITION = cluster.VOLUME_PARTITION
        AVAILABILITY_ZONE = cluster.AVAILABILITY_ZONE
        conn = self.conn
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

    def _has_all_required_settings(self, cluster):
        has_all_required = True
        for opt in self.cluster_settings:
            name = opt[0]; required = opt[2]; default=opt[3]
            if required and cluster[name] is None:
                log.warn('Missing required setting %s under section [%s]' % (name,section_name))
                has_all_required = False
        return has_all_required

    def validate_aws_or_exit(self):
        conn = self.conn
        if conn is None or not self._has_valid_credentials():
            log.error('Invalid AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY combination. Please check your settings')
            sys.exit(1)
        
    def validate_all_or_exit(self):
        for cluster in self.clusters:
            cluster = self.get_cluster(cluster)
            if not self.is_valid(cluster):
                log.error('configuration error...exiting')
                sys.exit(1)

    def _has_valid_credentials(self):
        conn = self.conn
        return not conn.describe_instances().is_error

    def _has_keypair(self, cluster):
        KEYNAME = cluster.KEYNAME
        conn = self.conn
        keypairs = conn.describe_keypairs().parse()
        has_keypair = False
        for key in keypairs:
            if key[1] == KEYNAME:
                has_keypair = True
        return has_keypair
        
INSTANCE_TYPES=StarClusterConfig.instance_types
#cfg = StarClusterConfig()
#cfg.load()
#cfg.validate_all_or_exit()
