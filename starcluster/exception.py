import os
from starcluster.templates.config import config_template, copy_paste_template

class BaseException(Exception):
    def __init__(self, *args):
        self.msg = args[0]
    def __str__(self):
        return self.msg
    def explain(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)

class ConfigError(BaseException):
    """Base class for all config related errors"""

class ConfigNotFound(ConfigError):
    def __init__(self, *args, **kwargs):
        super(ConfigNotFound, self).__init__(*args, **kwargs)
        self.cfg = args[1]
        self.template = copy_paste_template

    def create_config(self):
        cfg_parent_dir = os.path.dirname(self.cfg)
        if not os.path.exists(cfg_parent_dir):
            os.makedirs(cfg_parent_dir)
        cfg_file = open(self.cfg, 'w')
        cfg_file.write(config_template)
        cfg_file.close()
        log.info("Config template written to %s. Please customize this file." %
                 self.cfg)

    def display_options(self):
        print 'Options:'
        print '--------' 
        print '[1] Show the StarCluster config template'
        print '[2] Write config template to %s' % self.cfg
        print '[q] Quit'
        resp = raw_input('\nPlase enter your selection: ')
        if resp == '1':
            print self.template
        elif resp == '2':
            print
            self.create_config()

class PluginError(BaseException):
    """Base class for plugin errors"""

class PluginLoadError(PluginError):
    """Raised when an error is encountered while loading a plugin"""

class PluginSyntaxError(PluginError):
    """Raised when plugin contains syntax errors"""

class ClusterValidationError(BaseException):
    """Base class for cluster validation related settings"""

class IncompatibleSettings(ClusterValidationError):
    """Raised when two or more settings conflict with each other"""
    pass

class ClusterDoesNotExist(BaseException):
    """Exception raised when user requests a cluster that does not exist"""
