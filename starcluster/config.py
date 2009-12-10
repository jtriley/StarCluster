#!/usr/bin/env python
import os
import sys
import ConfigParser

import cluster
from logger import log
from utils import AttributeDict
from static import AWS_SETTINGS, CLUSTER_SETTINGS, INSTANCE_TYPES
from templates.config import config_template
from exceptions import ClusterDoesNotExist

def get_aws_from_environ():
    """Returns AWS credentials defined in the user's shell
    environment."""
    awscreds = {}
    for key in AWS_SETTINGS:
        if os.environ.has_key(key):
            awscreds[key] = os.environ.get(key)
    return awscreds

def get_config(config_file=None, cache=False):
    """Factory for StarClusterConfig object"""
    return StarClusterConfig(config_file, cache)

class StarClusterConfig(AttributeDict):
    """
    Loads StarCluster configuration settings defined in config_file
    which defaults to ~/.starclustercfg

    Settings are available as follows:

    cfg = StarClusterConfig()
    or
    cfg = StarClusterConfig('/path/to/my/config.cfg')
    cfg.load()
    aws_info = cfg.aws_info
    cluster_cfg = cfg.mycluster
    print cluster_cfg
    """

    DEFAULT_CFG_FILE = os.path.join(os.path.expanduser('~'),'.starclustercfg')

    # until i can find a way to query AWS for these...
    instance_types = INSTANCE_TYPES
    aws_settings = AWS_SETTINGS
    cluster_settings = CLUSTER_SETTINGS

    def __init__(self, config_file=None, cache=False):
        if config_file:
            if os.path.exists(config_file):
                if os.path.isfile(config_file):
                    self.cfg_file = config_file
                else:
                    log.warn('config %s exists but is not a regular file, defaulting to %s' %
                    (config_file,self.DEFAULT_CFG_FILE))
                    self.cfg_file = self.DEFAULT_CFG_FILE
            else:
                log.warn('config %s does not exist, defaulting to %s' %
                (config_file, self.DEFAULT_CFG_FILE))
                self.cfg_file = self.DEFAULT_CFG_FILE
        else:
            self.cfg_file = self.DEFAULT_CFG_FILE

        self.type_validators = {
            int: self._get_int,
            str: self._get_string,
        }
        self._config = None
        self._conn = None
        self.clusters = None
        self.cache = cache
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
    def config(self):
        # TODO: create the template file for them?
        CFG_FILE = self.cfg_file
        #if not os.path.exists(CFG_FILE):
            #print config_template
            #log.info('It appears this is your first time using StarCluster.')
            #log.info('Please create %s using the template above.' % CFG_FILE)
            #sys.exit(1)
        if not self.cache or self._config is None:
            try:
                self._config = ConfigParser.ConfigParser()
                self._config.read(CFG_FILE)
            except ConfigParser.MissingSectionHeaderError,e:
                log.warn('No sections defined in settings file %s' % CFG_FILE)
        return self._config

    def load_settings(self, section_name, settings, section_key=None):
        if section_key is None:
            section_key = section_name
        self[section_key] = AttributeDict()
        section_conf = self[section_key]
        for setting in settings:
            requirements = settings[setting]
            name = setting
            func = self.type_validators.get(requirements[0])
            required = requirements[1];
            default = requirements[2]
            value = func(self.config, section_name, name)
            if value:
                section_conf[name] = value

    def load_defaults(self, section_key, settings):
        section_conf = self.get(section_key, None)
        if not section_conf:
            section_conf = self[section_key] = AttributeDict()
        for setting in settings:
            name = setting; default = settings[setting][2]
            if section_conf.get(name, None) is None:
                if default:
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

    def get_aws_credentials(self):
        """Returns AWS credentials defined in the configuration
        file. Defining any of the AWS settings in the environment
        overrides the configuration file."""
        # first override with environment settings if they exist
        self.aws.update(get_aws_from_environ())
        return self.aws

    def get_cluster_names(self):
        return self.clusters

    def get_cluster(self, cluster_name):
        try:
            clust = cluster.get_cluster(**self[cluster_name])
            return clust
        except KeyError,e:
            raise ClusterDoesNotExist('config for cluster %s does not exist' % cluster_name)

    def get_clusters(self):
        clusters = []
        for cluster in self.clusters:
            clusters.append(self.get_cluster(cluster))
        return clusters
