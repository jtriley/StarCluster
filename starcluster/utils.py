#!/usr/bin/env python
"""
Utils module for StarCluster
"""

import re
import string
import urlparse
import time
from datetime import datetime
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
    try:
        return len(dev) == 8 and regex.match(dev)
    except TypeError,e:
        return False

def is_valid_partition(part):
    regex = re.compile('/dev/sd[a-z][1-9][0-9]?')
    try:
        return len(part) in [9,10] and regex.match(part)
    except TypeError,e:
        return False

def is_valid_bucket_name(bucket_name):
    """
    Check if bucket_name is a valid S3 bucket name (as defined by the AWS docs)
    """
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
    """
    Check if image_name is a valid AWS image name (as defined by the AWS docs)
    """
    length = len(image_name)
    valid_length = length>=3 and length <=128
    valid_chars = string.letters + string.digits + "().-/_"
    if not valid_length:
        return False
    for c in image_name:
        if c not in valid_chars:
            return False
    return True

def make_one_liner(script):
    """
    Returns command to execute python script as a one-line python program

    e.g. 
    
        import os
        script = '''
        import os
        print os.path.exists('hi')
        '''
        os.system(make_one_liner(script))

    Will print out:

        <module 'os' from ...>
        False
    """
    return 'python -c "%s"' % script.strip().replace('\n',';')

def is_url(url):
    try:
        parts = urlparse.urlparse(url)
        scheme = parts[0]
        netloc = parts[1]
        if scheme and netloc:
            return True
        else:
            return False
    except:
        return False

def is_iso_time(iso):
    try:
        iso_to_datetime_tuple(iso)
        return True
    except ValueError,e:
        return False

def iso_to_datetime_tuple(iso):
    #remove timezone
    iso = iso.split('.')[0]
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S")

def datetime_tuple_to_iso(tup):
    iso = datetime.strftime(tup, "%Y-%m-%dT%H:%M:%S")
    return iso

try:
    import IPython.Shell
    ipy_shell = IPython.Shell.IPShellEmbed(argv=[])
except ImportError,e:
    def ipy_shell():
        log.error("Unable to load IPython.")
        log.error("Please check that IPython is installed and working.")
        log.error("If not, you can install it via: easy_install ipython")
