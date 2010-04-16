#!/usr/bin/env python
"""
Utils module for StarCluster
"""

import re
import string
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

def is_valid_bucket_name(bucket_name):
    length = len(bucket_name)
    valid_length = length >= 3 and length <= 255
    if not valid_length:
        return False
    numbers_or_letters = string.ascii_lowercase + string.digits 
    valid_chars = numbers_or_letters + '._-'
    if not bucket_name[0] in numbers_or_letters:
        return False
    for c in bucket_name:
        if c not in valid_chars:
            return False
    if validate_ip(bucket_name):
        return False
    return True

def validate_ip(ip_address):
    pattern = r"\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|"
    pattern += r"[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25"
    pattern += r"[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    if re.match(pattern, ip_address):
        return True
    else:
        return False

def is_valid_image_name(image_name):
    length = len(image_name)
    valid_length = length>=3 and length <=128
    valid_chars = string.letters + string.digits + "().-/_"
    if not valid_length:
        return False
    for c in image_name:
        if c not in valid_chars:
            return False
    return True

try:
    import IPython.Shell
    ipy_shell = IPython.Shell.IPShellEmbed(argv=[])
except ImportError,e:
    def ipy_shell():
        log.error("Unable to load IPython.")
        log.error("Please check that IPython is installed and working.")
        log.error("If not, you can install it via: easy_install ipython")
