#!/usr/bin/env python
import os
import sys
import urllib
import ConfigParser

from starcluster.cluster import Cluster
from starcluster import static 
from starcluster import awsutils 
from starcluster import utils
from starcluster.utils import AttributeDict
from starcluster import exception 

from starcluster.logger import log

def get_easy_s3():
    """
    Factory for EasyS3 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyS3 object if
    successful.
    """
    cfg = StarClusterConfig(); cfg.load()
    return cfg.get_easy_s3()

def get_easy_ec2():
    """
    Factory for EasyEC2 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyEC2 object if
    successful.
    """
    cfg = StarClusterConfig(); cfg.load()
    return cfg.get_easy_ec2()


def get_config(config_file=None, cache=False):
    """Factory for StarClusterConfig object"""
    return StarClusterConfig(config_file, cache)

class StarClusterConfig(object):
    """
    Loads StarCluster configuration settings defined in config_file
    which defaults to ~/.starclustercfg

    Settings are available as follows:

    cfg = StarClusterConfig()
    or
    cfg = StarClusterConfig('/path/to/my/config.cfg')
    cfg.load()
    aws_info = cfg.aws
    cluster_cfg = cfg.clusters['mycluster']
    key_cfg = cfg.keys['gsg-keypair']
    print cluster_cfg
    """

    global_settings = static.GLOBAL_SETTINGS
    aws_settings = static.AWS_SETTINGS
    key_settings = static.KEY_SETTINGS
    volume_settings = static.EBS_VOLUME_SETTINGS
    plugin_settings = static.PLUGIN_SETTINGS
    cluster_settings = static.CLUSTER_SETTINGS

    # until i can find a way to query AWS for instance types...
    instance_types = static.INSTANCE_TYPES

    def __init__(self, config_file=None, cache=False):
        self.cfg_file = config_file
        self.type_validators = {
            int: self._get_int,
            str: self._get_string,
            bool: self._get_bool,
        }
        self._config = None
        self.globals = AttributeDict()
        self.aws = AttributeDict()
        self.clusters = AttributeDict()
        self.keys = AttributeDict()
        self.vols = AttributeDict()
        self.plugins = AttributeDict()
        self.cache = cache

    def _get_urlfp(self, url):
        log.debug("Loading url: %s" % url)
        import socket
        try:
            fp = urllib.urlopen(url)
            if fp.getcode() == 404:
                raise exception.ConfigError("url %s does not exist" % url)
            fp.name = url
            return fp
        except IOError,e:
            raise exception.ConfigError("error loading config from url %s\n%s"
                                        % (url,e))

    def _get_fp(self, config_file):
        if not os.path.isdir(static.STARCLUSTER_CFG_DIR):
            os.makedirs(static.STARCLUSTER_CFG_DIR)
        cfg_file = config_file or static.STARCLUSTER_CFG_FILE
        log.debug("Loading file: %s" % cfg_file)
        if os.path.exists(cfg_file):
            if not os.path.isfile(cfg_file):
                raise exception.ConfigError('config %s exists but is not a regular file' %
                                 cfg_file)
        else:
            raise exception.ConfigNotFound(
                ("config file %s does not exist\n") %
                cfg_file, cfg_file,
            )
        return open(cfg_file)

    def _get_bool(self, config, section, option):
        try:
            opt = config.getboolean(section,option)
            return opt
        except ConfigParser.NoSectionError,e:
            pass
        except ConfigParser.NoOptionError,e:
            pass
        except ValueError,e:
            raise exception.ConfigError(
                "Expected True/False value for setting %s in section [%s]" % (option,section))

    def _get_int(self, config, section, option):
        try:
            opt = config.getint(section,option)
            return opt
        except ConfigParser.NoSectionError,e:
            pass
        except ConfigParser.NoOptionError,e:
            pass
        except ValueError,e:
            raise exception.ConfigError(
                "Expected integer value for setting %s in section [%s]" % (option,section))

    def _get_string(self, config, section, option):
        try:
            opt = config.get(section,option)
            return opt
        except ConfigParser.NoSectionError,e:
            pass
        except ConfigParser.NoOptionError,e:
            pass

    def __load_config(self):
        """
        Populates self._config with a new ConfigParser instance
        """
        cfg = self.cfg_file
        if utils.is_url(cfg):
            cfg = self._get_urlfp(cfg)
        else:
            cfg = self._get_fp(cfg)
        try:
            cp = ConfigParser.ConfigParser()
            cp.readfp(cfg)
            return cp
        except ConfigParser.MissingSectionHeaderError,e:
            raise exception.ConfigHasNoSections(cfg.name)
        except ConfigParser.ParsingError,e:
            raise exception.ConfigError(e)

    def reload(self):
        """
        Reloads the configuration file
        """
        self._config = self.__load_config()
        self.load()

    @property
    def config(self):
        cfg = self.cfg_file
        if self._config is None:
            self._config = self.__load_config()
        return self._config

    def load_settings(self, section_name, settings, store):
        section = self.config._sections.get(section_name)
        if not section:
            raise exception.ConfigSectionMissing('Missing section %s in config'\
                                                 % section_name)
        store.update(section)
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            name = setting
            func = self.type_validators.get(requirements[0])
            required = requirements[1];
            default = requirements[2]
            value = func(self.config, section_name, name)
            if value is not None:
                section_conf[name.lower()] = value

    def check_required(self, section_name, settings, store):
        section_conf = store
        for setting in settings:
            name = setting
            requirements = settings[setting]
            required = requirements[1];
            value = section_conf.get(name.lower())
            if value is None and required:
                raise exception.ConfigError('missing required option %s in section "%s"' %
                                  (name.lower(), section_name))

    def load_defaults(self, settings, store):
        section_conf = store
        for setting in settings:
            name = setting.lower(); default = settings[setting][2]
            if section_conf.get(name, None) is None:
                if default:
                    log.debug('%s setting not specified. Defaulting to %s' % (name, default))
                section_conf[name] = default

    def load_extends_variables(self, section_name, store):
        section = store[section_name]
        extends = section['extends'] = section.get('extends')
        default = section.get('default')
        if extends is None:
            return
        log.debug('%s extends %s' % (section_name, extends))
        extensions = [section]
        while True:
            extends = section.get('extends',None)
            if extends:
                try:
                    section = store[extends]
                    extensions.insert(0, section)
                except KeyError,e:
                    log.warn("can't extend non-existent section %s" % extends)
                    break
            else:
                break
        transform = AttributeDict()
        for extension in extensions:
            transform.update(extension)
        # do not inherit default setting from other cluster sections
        transform.update(dict(default=default))
        store[section_name] = transform

    def load_keypairs(self, section_name, store):
        cluster_section = store
        keyname = cluster_section.get('keyname')
        if not keyname:
            return
        keypair = self.keys.get(keyname)
        if keypair is None:
            raise exception.ConfigError("keypair %s not defined in config" % keyname)
        cluster_section['keyname'] = keyname
        cluster_section['key_location'] = keypair.get('key_location')

    def load_volumes(self, section_name, store):
        cluster_section = store
        volumes = cluster_section.get('volumes')
        if not volumes or isinstance(volumes, AttributeDict):
            return
        vols = AttributeDict()
        cluster_section['volumes'] = vols
        volumes = [vol.strip() for vol in volumes.split(',')]
        for volume in volumes:
            if not self.vols.has_key(volume):
                raise exception.ConfigError("volume %s not defined in config" % volume)
            vol = self.vols.get(volume)
            vols[volume] = vol

    def load_plugins(self, section_name, store):
        cluster_section = store
        plugins = cluster_section.get('plugins')
        if not plugins or isinstance(plugins, list):
            return
        plugs = []
        cluster_section['plugins'] = plugs
        plugins = [plugin.strip() for plugin in plugins.split(',')]
        for plugin in plugins:
            if self.plugins.has_key(plugin):
                p = self.plugins.get(plugin)
                p['__name__'] = p['__name__'].split()[-1]
                plugs.append(p)
            else:
                raise exception.ConfigError("plugin %s not defined in config" % plugin)

    def load(self):
        log.debug('Loading config')
        try:
            self.load_settings('global', self.global_settings, self.globals)
        except exception.ConfigSectionMissing,e:
            pass
        try:
            self.load_settings('aws info', self.aws_settings, self.aws)
            self.check_required('aws info', self.aws_settings, self.aws)
        except exception.ConfigSectionMissing,e:
            log.warn("no [aws info] section found in config")
            log.warn("attempting to load credentials from environment...")
            self.aws.update(self.get_aws_from_environ())
        keys = [section.split()[1] for section in self.config.sections() if 
                section.startswith('key')]
        for key in keys:
            self.keys[key] = AttributeDict()
            section_name = 'key ' + key
            self.load_settings(section_name, self.key_settings, self.keys[key]) 
            self.check_required(section_name, self.key_settings, self.keys[key]) 
        vols = [section.split()[1] for section in self.config.sections() if 
                section.startswith('volume')]
        for vol in vols:
            self.vols[vol] = AttributeDict()
            section_name = 'volume ' + vol
            self.load_settings(section_name, self.volume_settings, 
                               self.vols[vol])
            self.load_defaults(self.volume_settings, self.vols[vol])
            self.check_required(section_name, self.volume_settings, 
                                self.vols[vol])
        plugins = [section.split()[1] for section in self.config.sections() if
                   section.startswith('plugin')]
        for plugin in plugins:
            self.plugins[plugin] = AttributeDict()
            section_name = 'plugin ' + plugin
            self.load_settings(section_name, self.plugin_settings,
                               self.plugins[plugin])
            self.check_required(section_name, self.plugin_settings,
                                self.plugins[plugin])
        clusters = [section.split()[1] for section in self.config.sections() if 
                    section.startswith('cluster')]
        for cluster in clusters:
            self.clusters[cluster] = AttributeDict()
            section_name = 'cluster ' + cluster
            self.load_settings(section_name, self.cluster_settings,
                               self.clusters[cluster])
        for cluster in clusters:
            section_name = 'cluster ' + cluster
            self.load_extends_variables(cluster, self.clusters)
            self.load_defaults(self.cluster_settings, self.clusters[cluster])
            self.load_keypairs(cluster, self.clusters[cluster])
            self.load_volumes(cluster, self.clusters[cluster])
            self.load_plugins(cluster, self.clusters[cluster])
            self.check_required(section_name, self.cluster_settings,
                               self.clusters[cluster])

    def get_aws_from_environ(self):
        """Returns AWS credentials defined in the user's shell
        environment."""
        awscreds = {}
        for key in static.AWS_SETTINGS:
            if os.environ.has_key(key):
                awscreds[key.lower()] = os.environ.get(key)
        return awscreds

    def get_aws_credentials(self):
        """
        Returns AWS credentials defined in the configuration
        file. Defining any of the AWS settings in the environment
        overrides the configuration file.
        """
        # first override with environment settings if they exist
        self.aws.update(self.get_aws_from_environ())
        return self.aws

    def get_cluster_names(self):
        return self.clusters

    def get_cluster_template(self, template_name, tag_name=None):
        """
        Returns Cluster instance configured with the settings in the config file.

        template_name is the name of a cluster section defined in the config

        tag_name, if specified, will be passed to Cluster instance as cluster_tag
        """
        try:
            kwargs = {}
            if tag_name:
                kwargs.update(dict(cluster_tag=tag_name))
            kwargs.update(**self.aws)
            kwargs.update(self.clusters[template_name])
            clust = Cluster(**kwargs)
            return clust
        except KeyError,e:
            raise exception.ClusterTemplateDoesNotExist(template_name)

    def get_default_cluster_template(self, tag_name=None):
        """
        Returns the cluster template with "DEFAULT=True" in the config
        If more than one found, raises MultipleDefaultTemplates exception.
        If no cluster template has "DEFAULT=True", raises NoDefaultTemplateFound
        exception.
        """
        default = self.globals.get('default_template')
        if not default:
            raise exception.NoDefaultTemplateFound(options=self.clusters.keys())
        if not self.clusters.has_key(default):
            raise exception.ClusterTemplateDoesNotExist(default)
        return default

    def get_clusters(self):
        clusters = []
        for cluster in self.clusters:
            clusters.append(self.get_cluster_template(cluster))
        return clusters

    def get_plugin(self, plugin):
        try:
            return self.plugins[plugin]
        except KeyError:
            raise exception.PluginNotFound(plugin)

    def get_key(self, keyname):
        try:
            return self.keys[keyname]
        except KeyError:
            raise exception.KeyNotFound(keyname)

    def get_easy_s3(self):
        """
        Factory for EasyEC2 class that attempts to load AWS credentials from
        the StarCluster config file. Returns an EasyS3 object if
        successful.
        """
        aws = self.get_aws_credentials()
        try:
            s3 = awsutils.EasyS3(**aws)
            return s3
        except TypeError,e:
            raise exception.ConfigError("no aws credentials found")

    def get_easy_ec2(self):
        """
        Factory for EasyEC2 class that attempts to load AWS credentials from
        the StarCluster config file. Returns an EasyEC2 object if
        successful.
        """
        aws = self.get_aws_credentials()
        try:
            ec2 = awsutils.EasyEC2(**aws)
            return ec2
        except TypeError,e:
            raise exception.ConfigError("no aws credentials found")

if __name__ == "__main__":
    from pprint import pprint
    cfg = StarClusterConfig(); cfg.load()
    pprint(cfg.aws)
    pprint(cfg.clusters)
    pprint(cfg.keys)
    pprint(cfg.vols)
