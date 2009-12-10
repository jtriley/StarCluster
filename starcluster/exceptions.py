class BaseException(Exception):
    def __init__(self, *args):
        self.msg = args[0]
    def __str__(self):
        return self.msg
    def explain(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)

class ClusterValidationError(BaseException):
    """Base class for cluster validation related settings"""

class InvalidSettings(ClusterValidationError):
    pass

class IncompatibleSettings(ClusterValidationError):
    """Raised when two or more settings conflict with each other"""
    pass

class ClusterDoesNotExist(BaseException):
    """Exception raised when user requests a cluster that does not exist"""

class ConfigException(BaseException):
    """Base class for all config related errors"""

class ConfigFileNotFound(ConfigException):
    """Exception raised when a config file has been specified that does not 
    exist"""

class InvalidConfig(ConfigException):
    """Exception raised when an invalid config file has been specified"""

