# Copyright 2009-2013 Justin Riley
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

"""
Contains code that should eventually be removed. Mostly used for maintaining
backwards compatibility while still moving the code forward.
"""
from starcluster import utils
from starcluster import exception
from starcluster import clustersetup
from starcluster.logger import log


def _load_plugins(plugins, debug=True):
    """
    Do not use - will be removed in the next release!

    Merge this into StarClusterConfig._load_plugins in a future release.
    Currently used to provide backwards compatibility for the plugin kwarg for
    Cluster. Cluster now expects the plugins kwarg to be a list of plugin
    objects not a list of dicts. This should be merged into
    StarClusterConfig._load_plugins in a future release after warning about the
    change in a previous release.
    """
    plugs = []
    for plugin in plugins:
        setup_class = plugin.get('setup_class')
        plugin_name = plugin.get('__name__').split()[-1]
        mod_name = '.'.join(setup_class.split('.')[:-1])
        class_name = setup_class.split('.')[-1]
        try:
            mod = __import__(mod_name, globals(), locals(), [class_name])
        except SyntaxError, e:
            raise exception.PluginSyntaxError(
                "Plugin %s (%s) contains a syntax error at line %s" %
                (plugin_name, e.filename, e.lineno))
        except ImportError, e:
            raise exception.PluginLoadError(
                "Failed to import plugin %s: %s" %
                (plugin_name, e[0]))
        klass = getattr(mod, class_name, None)
        if not klass:
            raise exception.PluginError(
                'Plugin class %s does not exist' % setup_class)
        if not issubclass(klass, clustersetup.ClusterSetup):
            raise exception.PluginError(
                "Plugin %s must be a subclass of "
                "starcluster.clustersetup.ClusterSetup" % setup_class)
        args, kwargs = utils.get_arg_spec(klass.__init__, debug=debug)
        config_args = []
        missing_args = []
        for arg in args:
            if arg in plugin:
                config_args.append(plugin.get(arg))
            else:
                missing_args.append(arg)
        if debug:
            log.debug("config_args = %s" % config_args)
        if missing_args:
            raise exception.PluginError(
                "Not enough settings provided for plugin %s (missing: %s)"
                % (plugin_name, ', '.join(missing_args)))
        config_kwargs = {}
        for arg in kwargs:
            if arg in plugin:
                config_kwargs[arg] = plugin.get(arg)
        if debug:
            log.debug("config_kwargs = %s" % config_kwargs)
        try:
            plug_obj = klass(*config_args, **config_kwargs)
        except Exception as exc:
            log.error("Error occured:", exc_info=True)
            raise exception.PluginLoadError(
                "Failed to load plugin %s with "
                "the following error: %s - %s" %
                (setup_class, exc.__class__.__name__, exc.message))
        if not hasattr(plug_obj, '__name__'):
            setattr(plug_obj, '__name__', plugin_name)
        plugs.append(plug_obj)
    return plugs
