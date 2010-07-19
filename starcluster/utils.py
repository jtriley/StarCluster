#!/usr/bin/env python
"""
Utils module for StarCluster
"""

import re
import types
import string
import urlparse
import time
from datetime import datetime
from starcluster.logger import log
from starcluster.iptools import validate_ip, validate_cidr

class AttributeDict(dict):
    """ Subclass of dict that allows read-only attribute-like access to
    dictionary key/values"""
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            return super(AttributeDict, self).__getattribute__(name)

def print_timing(msg=None):
    """
    Decorator for printing execution time (in mins) of a function
    Optionally takes a user-friendly msg as argument. This msg will
    appear in the sentence "[msg] took XXX mins". If no msg is specified,
    msg will default to the decorated function's name. e.g:

    @print_timing
    def myfunc():
        print 'hi'
    >>> myfunc()
    hi
    myfunc took 0.000 mins

    @print_timing('My function')
    def myfunc():
        print 'hi'
    >>> myfunc()
    hi
    My function took 0.000 mins
    """
    if type(msg) == types.FunctionType:
        func = msg
        def wrap_f(*arg, **kargs):
            """Raw timing function """
            time1 = time.time()
            res = func(*arg, **kargs)
            time2 = time.time()
            prefix = func.func_name
            log.info('%s took %0.3f mins' % (prefix, (time2-time1)/60.0))
            return res
        return wrap_f
    def wrap(func):
        def wrap_f(*arg, **kargs):
            """Raw timing function """
            time1 = time.time()
            res = func(*arg, **kargs)
            time2 = time.time()
            prefix = msg
            log.info('%s took %0.3f mins' % (prefix, (time2-time1)/60.0))
            return res
        return wrap_f
    return wrap

def is_valid_device(dev):
    regex = re.compile('/dev/sd[a-z]$')
    try:
        return regex.match(dev) is not None
    except TypeError,e:
        return False

def is_valid_partition(part):
    regex = re.compile('/dev/sd[a-z][1-9][0-9]?$')
    try:
        return regex.match(part) is not None
    except TypeError,e:
        return False

def is_valid_bucket_name(bucket_name):
    """
    Check if bucket_name is a valid S3 bucket name (as defined by the AWS
    docs):

    1. 3 <= len(bucket_name) <= 255
    2. all chars one of: a-z 0-9 .  _ -
    3. first char one of: a-z 0-9
    4. name must not be a valid ip
    """
    regex = re.compile('[a-z0-9][a-z0-9\._-]{2,254}$')
    if not regex.match(bucket_name):
        return False
    if validate_ip(bucket_name):
        return False
    return True

def is_valid_image_name(image_name):
    """
    Check if image_name is a valid AWS image name (as defined by the AWS docs)

    1. 3<= len(image_name) <=128
    2. all chars one of: a-z A-Z 0-9 ( ) . - / _
    """
    regex = re.compile('[\w\(\)\.-\/_]{3,128}$')
    try:
        return regex.match(image_name) is not None
    except TypeError,e:
        return False

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

def qacct_to_datetime_tuple(qacct):
    """
    Takes the SGE qacct formatted time and makes a datetime tuple
    format is:
    Tue Jul 13 16:24:03 2010
    """
    return datetime.strptime(qacct, "%a %b %d %H:%M:%S %Y")

def get_remote_time(cl):
    """
    this function remotely executes 'date' on the master node
    and returns a datetime object with the master's time
    instead of fetching it from local machine, maybe inaccurate. 
    """
    str = '\n'.join(cl.master_node.ssh.execute('date'))
    return datetime.strptime(str, "%a %b %d %H:%M:%S UTC %Y")

try:
    import IPython.Shell
    ipy_shell = IPython.Shell.IPShellEmbed(argv=[])
except ImportError,e:
    def ipy_shell():
        log.error("Unable to load IPython.")
        log.error("Please check that IPython is installed and working.")
        log.error("If not, you can install it via: easy_install ipython")

def permute(a):
    """
    Returns generator of all permutations of a

    The following code is an in-place permutation of a given list, implemented
    as a generator. Since it only returns references to the list, the list
    should not be modified outside the generator. The solution is non-recursive,
    so uses low memory. Work well also with multiple copies of elements in the
    input list.

    Retrieved from:
        http://stackoverflow.com/questions/104420/how-to-generate-all-permutations-of-a-list-in-python
    """
    a.sort()
    yield list(a)
    if len(a) <= 1:
        return
    first = 0
    last = len(a)
    while 1:
        i = last - 1
        while 1:
            i = i - 1
            if a[i] < a[i+1]:
                j = last - 1
                while not (a[i] < a[j]):
                    j = j - 1
                a[i], a[j] = a[j], a[i] # swap the values
                r = a[i+1:last]
                r.reverse()
                a[i+1:last] = r
                yield list(a)
                break
            if i == first:
                a.reverse()
                return
