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
    permission_settings = static.PERMISSION_SETTINGS

    # until i can find a way to query AWS for instance types...
    instance_types = static.INSTANCE_TYPES

    def __init__(self, config_file=None, cache=False):
        self.cfg_file = config_file
        self.type_validators = {
            int: self._get_int,
            str: self._get_string,
            bool: self._get_bool,
            list: self._get_list,
        }
        self._config = None
        self.globals = AttributeDict()
        self.aws = AttributeDict()
        self.clusters = AttributeDict()
        self.keys = AttributeDict()
        self.vols = AttributeDict()
        self.plugins = AttributeDict()
        self.permissions = AttributeDict()
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
            raise exception.ConfigError(
                "error loading config from url %s\n%s" % (url,e))

    def _get_fp(self, config_file):
        if not os.path.isdir(static.STARCLUSTER_CFG_DIR):
            os.makedirs(static.STARCLUSTER_CFG_DIR)
        cfg_file = config_file or static.STARCLUSTER_CFG_FILE
        log.debug("Loading file: %s" % cfg_file)
        if os.path.exists(cfg_file):
            if not os.path.isfile(cfg_file):
                raise exception.ConfigError(
                    'config %s exists but is not a regular file' % cfg_file)
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
                "Expected True/False value for setting %s in section [%s]" % 
                (option,section))

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
                "Expected integer value for setting %s in section [%s]" % 
                (option,section))

    def _get_string(self, config, section, option):
        try:
            opt = config.get(section,option)
            return opt
        except ConfigParser.NoSectionError,e:
            pass
        except ConfigParser.NoOptionError,e:
            pass

    def _get_list(self, config, section, option):
        val = self._get_string(config, section, option)
        if val:
            val = [v.strip() for v in val.split(',')]
        return val

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

    def _load_settings(self, section_name, settings, store):
        """
        Load section settings into a dictionary
        """
        section = self.config._sections.get(section_name)
        if not section:
            raise exception.ConfigSectionMissing('Missing section %s in config' %
                                                 section_name)
        store.update(section)
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            func, required, default, options = requirements
            func = self.type_validators.get(func)
            value = func(self.config, section_name, setting)
            if value is not None:
                if options and not value in options:
                    raise exception.ConfigError(
                        '"%s" setting in section "%s" must be one of: %s' % 
                        (setting, section_name,
                         ', '.join([str(o) for o in options])))
                section_conf[setting] = value

    def _check_required(self, section_name, settings, store):
        """
        Check that all required settings were specified in the config.
        Raises ConfigError otherwise.

        Note that if a setting specified has required=True and 
        default is not None then this method will not raise an error
        because a default was given. In short, if a setting is required
        you must provide None as the 'default' value.
        """
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            required = requirements[1]
            value = section_conf.get(setting)
            if value is None and required:
                raise exception.ConfigError(
                    'missing required option %s in section "%s"' % 
                    (setting, section_name))

    def _load_defaults(self, settings, store):
        """
        Sets the default for each setting in settings regardless of whether 
        the setting was specified in the config or not.
        """
        section_conf = store
        for setting in settings:
            default = settings[setting][2]
            if section_conf.get(setting, None) is None:
                log.debug('%s setting not specified. Defaulting to %s' %
                          (setting, default))
                section_conf[setting] = default

    def _load_extends_settings(self, section_name, store):
        """
        Loads all settings from other template(s) specified by a section's 
        'extends' setting.

        This method walks a dependency tree of sections from bottom up. Each 
        step is a group of settings for a section in the form of a dictionary. 
        A 'master' dictionary is updated with the settings at each step. This
        causes the next group of settings to override the previous, and so on.
        The 'section_name' settings are at the top of the dep tree.
        """
        section = store[section_name]
        extends = section.get('extends')
        if extends is None:
            return
        log.debug('%s extends %s' % (section_name, extends))
        extensions = [section]
        while True:
            extends = section.get('extends', None)
            if not extends:
                break
            try:
                section = store[extends]
                if section in extensions:
                    exts = ', '.join([self._get_section_name(x['__name__']) 
                                      for x in extensions])
                    raise exception.ConfigError(
                        ("Cyclical dependency between sections %s. " %
                         exts) + "Check your extends settings."
                    )
                extensions.insert(0, section)
            except KeyError,e:
                raise exception.ConfigError(
                    "%s can't extend non-existent section %s" %
                    (section_name,extends)
                )
        transform = AttributeDict()
        for extension in extensions:
            transform.update(extension)
        store[section_name] = transform

    def _load_keypairs(self, section_name, store):
        cluster_section = store
        keyname = cluster_section.get('keyname')
        if not keyname:
            return
        keypair = self.keys.get(keyname)
        if keypair is None:
            raise exception.ConfigError("keypair %s not defined in config" % keyname)
        cluster_section['keyname'] = keyname
        cluster_section['key_location'] = keypair.get('key_location')

    def _load_volumes(self, section_name, store):
        cluster_section = store
        volumes = cluster_section.get('volumes')
        if not volumes or isinstance(volumes, AttributeDict):
            return
        vols = AttributeDict()
        cluster_section['volumes'] = vols
        for volume in volumes:
            if not self.vols.has_key(volume):
                raise exception.ConfigError("volume %s not defined in config" % volume)
            vol = self.vols.get(volume)
            vols[volume] = vol

    def _load_plugins(self, section_name, store):
        cluster_section = store
        plugins = cluster_section.get('plugins')
        if not plugins or isinstance(plugins[0], AttributeDict):
            return
        plugs = []
        cluster_section['plugins'] = plugs
        for plugin in plugins:
            if self.plugins.has_key(plugin):
                p = self.plugins.get(plugin)
                p['__name__'] = p['__name__'].split()[-1]
                plugs.append(p)
            else:
                raise exception.ConfigError("plugin %s not defined in config" % plugin)

    def _load_permissions(self, section_name, store):
        cluster_section = store
        permissions = cluster_section.get('permissions')
        if not permissions or isinstance(permissions, AttributeDict):
            return
        perms = AttributeDict()
        cluster_section['permissions'] = perms
        for perm in permissions:
            if self.permissions.has_key(perm):
                p = self.permissions.get(perm)
                #if p.has_key('protocol') and 
                p['__name__'] = p['__name__'].split()[-1]
                perms[perm] = p
            else:
                raise exception.ConfigError(
                    "permission %s not defined in config" % perm)

    def _load_section(self, section_name, section_settings):
        """
        Returns a dictionary containing all section_settings for a given 
        section_name by first loading the settings in the config, loading
        the defaults for all settings not specified, and then checking 
        that all required options have been specified
        """
        store = AttributeDict()
        self._load_settings(section_name, section_settings, store)
        self._load_defaults(section_settings, store)
        self._check_required(section_name, section_settings, store)
        return store

    def _get_section_name(self, section):
        """
        Returns section name minus prefix
        e.g. 
        $ print self._get_section('cluster smallcluster')
        $ smallcluster
        """
        return section.split()[1]

    def _get_sections(self, section_prefix):
        """
        Returns all sections starting with section_prefix
        e.g. 
        $ print self._get_sections('cluster')
        $ ['cluster smallcluster', 'cluster mediumcluster', ..]
        """
        return [s for s in self.config.sections() if
                s.startswith(section_prefix)]

    def _load_sections(self, section_prefix, section_settings, load_extends=False):
        """
        Loads all sections starting with section_prefix and returns a 
        dictionary containing the name and dictionary of settings for each
        section.
        keys --> section name (as returned by self._get_section_name)
        values --> dictionary of settings for a given section

        e.g.
        $ print self._load_sections('volumes', self.plugin_settings)

        {'myvol': {'__name__': 'volume myvol',
                    'device': None,
                    'mount_path': '/home',
                    'partition': 1,
                    'volume_id': 'vol-999999'},
         'myvol2': {'__name__': 'volume myvol2',
                       'device': None,
                       'mount_path': '/myvol2',
                       'partition': 1,
                       'volume_id': 'vol-999999'},
        """
        sections = self._get_sections(section_prefix) 
        sections_store = AttributeDict()
        for sec in sections:
            name = self._get_section_name(sec)
            sections_store[name] = self._load_section(sec, section_settings)
        return sections_store

    def _load_cluster_sections(self, cluster_sections):
        """
        Loads all cluster sections. Similar to _load_sections but also handles 
        populating specified keypair,volume,plugins,permissions,etc settings
        """
        clusters = cluster_sections
        cluster_store = AttributeDict()
        for cluster in clusters:
            name = self._get_section_name(cluster)
            cluster_store[name] = AttributeDict()
            self._load_settings(cluster, self.cluster_settings,
                               cluster_store[name])
        for cluster in clusters:
            name = self._get_section_name(cluster)
            self._load_extends_settings(name, cluster_store)
            self._load_defaults(self.cluster_settings, cluster_store[name])
            self._load_keypairs(name, cluster_store[name])
            self._load_volumes(name, cluster_store[name])
            self._load_plugins(name, cluster_store[name])
            self._load_permissions(name, cluster_store[name])
            self._check_required(cluster, self.cluster_settings,
                               cluster_store[name])
        return cluster_store

    def load(self):
        """
        Populate this config object from the StarCluster config
        """
        log.debug('Loading config')
        try:
            self.globals = self._load_section('global', self.global_settings)
        except exception.ConfigSectionMissing,e:
            pass
        try:
            self.aws = self._load_section('aws info', self.aws_settings)
        except exception.ConfigSectionMissing,e:
            log.warn("no [aws info] section found in config")
            log.warn("attempting to load credentials from environment...")
            self.aws.update(self.get_aws_from_environ())
        self.keys = self._load_sections('key', self.key_settings)
        self.vols = self._load_sections('volume', self.volume_settings)
        self.plugins = self._load_sections('plugin', self.plugin_settings)
        self.permissions = self._load_sections('permission',
                                               self.permission_settings)
        sections = self._get_sections('cluster')
        self.clusters = self._load_cluster_sections(sections)

    def get_aws_from_environ(self):
        """
        Returns AWS credentials defined in the user's shell
        environment.
        """
        awscreds = {}
        for key in static.AWS_SETTINGS:
            if os.environ.has_key(key.upper()):
                awscreds[key] = os.environ.get(key.upper())
            elif os.environ.has_key(key):
                awscreds[key] = os.environ.get(key)
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
