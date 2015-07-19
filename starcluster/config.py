# Copyright 2009-2014 Justin Riley
#
# This file is part of StarCluster.
#
# StarCluster is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# StarCluster is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with StarCluster. If not, see <http://www.gnu.org/licenses/>.

import os
import glob
import urllib
import StringIO
import ConfigParser

from starcluster import utils
from starcluster import static
from starcluster import cluster
from starcluster import awsutils
from starcluster import deathrow
from starcluster import exception
from starcluster.cluster import Cluster
from starcluster.utils import AttributeDict

from starcluster.logger import log

DEBUG_CONFIG = False


def get_easy_s3(config_file=None, cache=False):
    """
    Factory for EasyS3 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyS3 object if
    successful.
    """
    cfg = get_config(config_file, cache)
    return cfg.get_easy_s3()


def get_easy_ec2(config_file=None, cache=False):
    """
    Factory for EasyEC2 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyEC2 object if
    successful.
    """
    cfg = get_config(config_file, cache)
    return cfg.get_easy_ec2()


def get_cluster_manager(config_file=None, cache=False):
    """
    Factory for ClusterManager class that attempts to load AWS credentials from
    the StarCluster config file. Returns a ClusterManager object if successful
    """
    cfg = get_config(config_file, cache)
    return cfg.get_cluster_manager()


def get_config(config_file=None, cache=False):
    """Factory for StarClusterConfig object"""
    return StarClusterConfig(config_file, cache).load()


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
        self.cfg_file = config_file \
            or os.environ.get('STARCLUSTER_CONFIG') \
            or static.STARCLUSTER_CFG_FILE
        self.cfg_file = os.path.expanduser(self.cfg_file)
        self.cfg_file = os.path.expandvars(self.cfg_file)
        self.type_validators = {
            int: self._get_int,
            float: self._get_float,
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

    def __repr__(self):
        return "<StarClusterConfig: %s>" % self.cfg_file

    def _get_urlfp(self, url):
        log.debug("Loading url: %s" % url)
        try:
            fp = urllib.urlopen(url)
            if fp.getcode() == 404:
                raise exception.ConfigError("url %s does not exist" % url)
            fp.name = url
            return fp
        except IOError, e:
            raise exception.ConfigError(
                "error loading config from url %s\n%s" % (url, e))

    def _get_fp(self, cfg_file):
        log.debug("Loading file: %s" % cfg_file)
        if os.path.exists(cfg_file):
            if not os.path.isfile(cfg_file):
                raise exception.ConfigError(
                    'config %s exists but is not a regular file' % cfg_file)
        else:
            raise exception.ConfigNotFound("config file %s does not exist\n" %
                                           cfg_file, cfg_file)
        return open(cfg_file)

    def _get_cfg_fp(self, cfg_file=None):
        cfg = cfg_file or self.cfg_file
        if utils.is_url(cfg):
            return self._get_urlfp(cfg)
        else:
            return self._get_fp(cfg)

    def _get_bool(self, config, section, option):
        try:
            opt = config.getboolean(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected True/False value for setting %s in section [%s]" %
                (option, section))

    def _get_int(self, config, section, option):
        try:
            opt = config.getint(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected integer value for setting %s in section [%s]" %
                (option, section))

    def _get_float(self, config, section, option):
        try:
            opt = config.getfloat(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected float value for setting %s in section [%s]" %
                (option, section))

    def _get_string(self, config, section, option):
        try:
            opt = config.get(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
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
        cfg = self._get_cfg_fp()
        try:
            cp = InlineCommentsIgnoredConfigParser()
            cp.readfp(cfg)
            self._config = cp
            try:
                self.globals = self._load_section('global',
                                                  self.global_settings)
                includes = self.globals.get('include')
                if not includes:
                    return cp
                mashup = StringIO.StringIO()
                cfg = self._get_cfg_fp()
                mashup.write(cfg.read() + '\n')
                for include in includes:
                    include = os.path.expanduser(include)
                    include = os.path.expandvars(include)
                    try:
                        for inc_file in glob.glob(include):
                            contents = self._get_cfg_fp(inc_file).read()
                            mashup.write(contents + '\n')
                    except exception.ConfigNotFound:
                        raise exception.ConfigError("include %s not found" %
                                                    include)
                mashup.seek(0)
                cp = InlineCommentsIgnoredConfigParser()
                cp.readfp(mashup)
                self._config = cp
            except exception.ConfigSectionMissing:
                pass
            return cp
        except ConfigParser.MissingSectionHeaderError:
            raise exception.ConfigHasNoSections(cfg.name)
        except ConfigParser.ParsingError, e:
            raise exception.ConfigError(e)

    def reload(self):
        """
        Reloads the configuration file
        """
        self.__load_config()
        return self.load()

    @property
    def config(self):
        if self._config is None:
            self._config = self.__load_config()
        return self._config

    def _load_settings(self, section_name, settings, store,
                       filter_settings=True):
        """
        Load section settings into a dictionary
        """
        section = self.config._sections.get(section_name)
        if not section:
            raise exception.ConfigSectionMissing(
                'Missing section %s in config' % section_name)
        store.update(section)
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            func, required, default, options, callback = requirements
            func = self.type_validators.get(func)
            value = func(self.config, section_name, setting)
            if value is not None:
                if options and value not in options:
                    raise exception.ConfigError(
                        '"%s" setting in section "%s" must be one of: %s' %
                        (setting, section_name,
                         ', '.join([str(o) for o in options])))
                if callback:
                    value = callback(value)
                section_conf[setting] = value
        if filter_settings:
            for key in store.keys():
                if key not in settings and key != '__name__':
                    store.pop(key)

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
            if section_conf.get(setting) is None:
                if DEBUG_CONFIG:
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
        The 'section_name' settings are at the top of the dependency tree.
        """
        section = store[section_name]
        extends = section.get('extends')
        if extends is None:
            return
        if DEBUG_CONFIG:
            log.debug('%s extends %s' % (section_name, extends))
        extensions = [section]
        while extends is not None:
            try:
                section = store[extends]
                if section in extensions:
                    exts = ', '.join([self._get_section_name(x['__name__'])
                                      for x in extensions])
                    raise exception.ConfigError(
                        "Cyclical dependency between sections %s. "
                        "Check your EXTENDS settings." % exts)
                extensions.insert(0, section)
            except KeyError:
                raise exception.ConfigError(
                    "%s can't extend non-existent section %s" %
                    (section_name, extends))
            extends = section.get('extends')
        transform = AttributeDict()
        for extension in extensions:
            transform.update(extension)
        store[section_name] = transform

    def _load_keypairs(self, store):
        cluster_section = store
        keyname = cluster_section.get('keyname')
        if not keyname:
            return
        keypair = self.keys.get(keyname)
        if keypair is None:
            raise exception.ConfigError(
                "keypair '%s' not defined in config" % keyname)
        cluster_section['keyname'] = keyname
        cluster_section['key_location'] = keypair.get('key_location')

    def _load_volumes(self, store):
        cluster_section = store
        volumes = cluster_section.get('volumes')
        if not volumes or isinstance(volumes, AttributeDict):
            return
        vols = AttributeDict()
        cluster_section['volumes'] = vols
        for volume in volumes:
            if volume not in self.vols:
                raise exception.ConfigError(
                    "volume '%s' not defined in config" % volume)
            vol = self.vols.get(volume).copy()
            del vol['__name__']
            vols[volume] = vol

    def _load_plugins(self, store):
        cluster_section = store
        plugins = cluster_section.get('plugins')
        if not plugins or isinstance(plugins[0], AttributeDict):
            return
        plugs = []
        for plugin in plugins:
            if plugin not in self.plugins:
                raise exception.ConfigError(
                    "plugin '%s' not defined in config" % plugin)
            plugs.append(self.plugins.get(plugin))
        cluster_section['plugins'] = plugs

    def _load_permissions(self, store):
        cluster_section = store
        permissions = cluster_section.get('permissions')
        if not permissions or isinstance(permissions, AttributeDict):
            return
        perms = AttributeDict()
        cluster_section['permissions'] = perms
        for perm in permissions:
            if perm in self.permissions:
                p = self.permissions.get(perm)
                p['__name__'] = p['__name__'].split()[-1]
                perms[perm] = p
            else:
                raise exception.ConfigError(
                    "permission '%s' not defined in config" % perm)

    def _load_instance_types(self, store):
        cluster_section = store
        instance_types = cluster_section.get('node_instance_type')
        if isinstance(instance_types, basestring):
            return
        itypes = []
        cluster_section['node_instance_types'] = itypes
        total_num_nodes = 0
        choices_string = ', '.join(static.INSTANCE_TYPES.keys())
        try:
            default_instance_type = instance_types[-1]
            if default_instance_type not in static.INSTANCE_TYPES:
                raise exception.ConfigError(
                    "invalid node_instance_type specified: '%s'\n"
                    "must be one of: %s" %
                    (default_instance_type, choices_string))
        except IndexError:
            default_instance_type = None
        cluster_section['node_instance_type'] = default_instance_type
        for type_spec in instance_types[:-1]:
            type_spec = type_spec.split(':')
            if len(type_spec) > 3:
                raise exception.ConfigError(
                    "invalid node_instance_type item specified: %s" %
                    type_spec)
            itype = type_spec[0]
            itype_image = None
            itype_num = 1
            if itype not in static.INSTANCE_TYPES:
                raise exception.ConfigError(
                    "invalid type specified (%s) in node_instance_type "
                    "item: '%s'\nmust be one of: %s" %
                    (itype, type_spec, choices_string))
            if len(type_spec) == 2:
                itype, next_var = type_spec
                try:
                    itype_num = int(next_var)
                except (TypeError, ValueError):
                    itype_image = next_var
            elif len(type_spec) == 3:
                itype, itype_image, itype_num = type_spec
            try:
                itype_num = int(itype_num)
                if itype_num < 1:
                    raise TypeError
                total_num_nodes += itype_num
            except (ValueError, TypeError):
                raise exception.ConfigError(
                    "number of instances (%s) of type '%s' must "
                    "be an integer > 1" % (itype_num, itype))
            itype_dic = AttributeDict(size=itype_num, image=itype_image,
                                      type=itype)
            itypes.append(itype_dic)

    def _load_section(self, section_name, section_settings,
                      filter_settings=True):
        """
        Returns a dictionary containing all section_settings for a given
        section_name by first loading the settings in the config, loading
        the defaults for all settings not specified, and then checking
        that all required options have been specified
        """
        store = AttributeDict()
        self._load_settings(section_name, section_settings, store,
                            filter_settings)
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

    def _load_sections(self, section_prefix, section_settings,
                       filter_settings=True):
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
            sections_store[name] = self._load_section(sec, section_settings,
                                                      filter_settings)
        return sections_store

    def _load_cluster_sections(self, cluster_sections):
        """
        Loads all cluster sections. Similar to _load_sections but also handles
        populating specified keypair, volume, plugins, permissions, etc.
        settings
        """
        clusters = cluster_sections
        cluster_store = AttributeDict()
        for cl in clusters:
            name = self._get_section_name(cl)
            cluster_store[name] = AttributeDict()
            self._load_settings(cl, self.cluster_settings, cluster_store[name])
        for cl in clusters:
            name = self._get_section_name(cl)
            self._load_extends_settings(name, cluster_store)
            self._load_defaults(self.cluster_settings, cluster_store[name])
            self._load_keypairs(cluster_store[name])
            self._load_volumes(cluster_store[name])
            self._load_plugins(cluster_store[name])
            self._load_permissions(cluster_store[name])
            self._load_instance_types(cluster_store[name])
            self._check_required(cl, self.cluster_settings,
                                 cluster_store[name])
        return cluster_store

    def load(self):
        """
        Populate this config object from the StarCluster config
        """
        log.debug('Loading config')
        try:
            self.globals = self._load_section('global', self.global_settings)
        except exception.ConfigSectionMissing:
            pass
        try:
            self.aws = self._load_section('aws info', self.aws_settings)
        except exception.ConfigSectionMissing:
            log.warn("No [aws info] section found in the config!")
        self.aws.update(self.get_settings_from_env(self.aws_settings))
        self.keys = self._load_sections('key', self.key_settings)
        self.vols = self._load_sections('volume', self.volume_settings)
        self.vols.update(self._load_sections('vol', self.volume_settings))
        self.plugins = self._load_sections('plugin', self.plugin_settings,
                                           filter_settings=False)
        self.permissions = self._load_sections('permission',
                                               self.permission_settings)
        sections = self._get_sections('cluster')
        self.clusters = self._load_cluster_sections(sections)
        return self

    def get_settings_from_env(self, settings):
        """
        Returns AWS credentials defined in the user's shell
        environment.
        """
        found = {}
        for key in settings:
            if key.upper() in os.environ:
                log.warn("Setting '%s' from environment..." % key.upper())
                found[key] = os.environ.get(key.upper())
            elif key in os.environ:
                log.warn("Setting '%s' from environment..." % key)
                found[key] = os.environ.get(key)
        return found

    def get_cluster_template(self, template_name, tag_name=None,
                             ec2_conn=None):
        """
        Returns Cluster instance configured with the settings in the
        config file.

        template_name is the name of a cluster section defined in the config

        tag_name if not specified will be set to template_name
        """
        try:
            kwargs = {}
            tag_name = tag_name or template_name
            kwargs.update(dict(cluster_tag=tag_name))
            kwargs.update(self.clusters[template_name])
            plugs = kwargs.get('plugins')
            kwargs['plugins'] = deathrow._load_plugins(plugs,
                                                       debug=DEBUG_CONFIG)
            if not ec2_conn:
                ec2_conn = self.get_easy_ec2()

            clust = Cluster(ec2_conn, **kwargs)
            return clust
        except KeyError:
            raise exception.ClusterTemplateDoesNotExist(template_name)

    def get_default_cluster_template(self):
        """
        Returns the default_template specified in the [global] section
        of the config. Raises NoDefaultTemplateFound if no default cluster
        template has been specified in the config.
        """
        default = self.globals.get('default_template')
        if not default:
            raise exception.NoDefaultTemplateFound(
                options=self.clusters.keys())
        if default not in self.clusters:
            raise exception.ClusterTemplateDoesNotExist(default)
        return default

    def get_clusters(self):
        clusters = []
        for cl in self.clusters:
            clusters.append(self.get_cluster_template(cl, tag_name=cl))
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
        try:
            s3 = awsutils.EasyS3(**self.aws)
            return s3
        except TypeError:
            raise exception.ConfigError("no aws credentials found")

    def get_easy_ec2(self):
        """
        Factory for EasyEC2 class that attempts to load AWS credentials from
        the StarCluster config file. Returns an EasyEC2 object if
        successful.
        """
        try:
            ec2 = awsutils.EasyEC2(**self.aws)
            return ec2
        except TypeError:
            raise exception.ConfigError("no aws credentials found")

    def get_cluster_manager(self):
        ec2 = self.get_easy_ec2()
        return cluster.ClusterManager(self, ec2)


class InlineCommentsIgnoredConfigParser(ConfigParser.ConfigParser):
    """
    Class for custom config file parsing that ignores inline comments.

    By default, ConfigParser.ConfigParser only ignores inline comments denoted
    by a semicolon. This class extends this support to allow inline comments
    denoted by '#' as well. Just as with semicolons, a spacing character must
    precede the pound sign for it to be considered an inline comment.

    For example, the following line would have the inline comment ignored:

        FOO = bar # some comment...

    And would be parsed as:

        FOO = bar

    The following would NOT have the comment removed:

        FOO = bar# some comment...
    """

    def readfp(self, fp, filename=None):
        """
        Overrides ConfigParser.ConfigParser.readfp() to ignore inline comments.
        """
        if filename is None:
            try:
                filename = fp.name
            except AttributeError:
                filename = '<???>'

        # We don't use the file iterator here because ConfigParser.readfp()
        # guarantees to only call readline() on fp, so we want to adhere to
        # this as well.
        commentless_fp = StringIO.StringIO()
        line = fp.readline()
        while line:
            pound_pos = line.find('#')

            # A pound sign only starts an inline comment if it is preceded by
            # whitespace.
            if pound_pos > 0 and line[pound_pos - 1].isspace():
                line = line[:pound_pos].rstrip() + '\n'
            commentless_fp.write(line)
            line = fp.readline()
        commentless_fp.seek(0)

        # Cannot use super() because ConfigParser is not a new-style class.
        ConfigParser.ConfigParser.readfp(self, commentless_fp, filename)


if __name__ == "__main__":
    from pprint import pprint
    cfg = StarClusterConfig().load()
    pprint(cfg.aws)
    pprint(cfg.clusters)
    pprint(cfg.keys)
    pprint(cfg.vols)
