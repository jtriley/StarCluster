#!/usr/bin/env python
"""
Utils module for StarCluster
"""

import re
import time
from starcluster.logger import log

class AttributeDict(dict):
    """ Subclass of dict that allows read-only attribute-like access to
    dictionary key/values"""
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            return super(AttributeDict, self).__getattribute__(name)

def print_timing(func):
    """Decorator for printing execution time (in mins) of a function"""
    def wrapper(*arg, **kargs):
        """Raw timing function """
        time1 = time.time()
        res = func(*arg, **kargs)
        time2 = time.time()
        log.info('%s took %0.3f mins' % (func.func_name, (time2-time1)/60.0))
        return res
    return wrapper

def is_valid_device(dev):
    regex = re.compile('/dev/sd[a-z]')
    return len(dev) == 8 and regex.match(dev)

def is_valid_partition(part):
    regex = re.compile('/dev/sd[a-z][1-9][0-9]?')
    return len(part) in [9,10] and regex.match(part)

try:
    import IPython.Shell
    ipy_shell = IPython.Shell.IPShellEmbed(argv=[])
except ImportError,e:
    def ipy_shell():
        log.error("Unable to load IPython.")
        log.error("Please check that IPython is installed and working.")
        log.error("If not, you can install it via: easy_install ipython")
