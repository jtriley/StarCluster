#!/usr/bin/env python
"""
Utils module for StarCluster
"""

import os
import re
import time
import types
import urlparse
from datetime import datetime

from starcluster import iptools
from starcluster import exception
from starcluster.logger import log


class AttributeDict(dict):
    """
    Subclass of dict that allows read-only attribute-like access to
    dictionary key/values
    """
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
            log.info('%s took %0.3f mins' % (prefix, (time2 - time1) / 60.0))
            return res
        return wrap_f

    def wrap(func):
        def wrap_f(*arg, **kargs):
            """Raw timing function """
            time1 = time.time()
            res = func(*arg, **kargs)
            time2 = time.time()
            prefix = msg
            log.info('%s took %0.3f mins' % (prefix, (time2 - time1) / 60.0))
            return res
        return wrap_f
    return wrap


def is_valid_device(dev):
    """
    Checks that dev matches the following regular expression:
    /dev/sd[a-z]$
    """
    regex = re.compile('/dev/sd[a-z]$')
    try:
        return regex.match(dev) is not None
    except TypeError:
        return False


def is_valid_partition(part):
    """
    Checks that part matches the following regular expression:
    /dev/sd[a-z][1-9][0-9]?$
    """
    regex = re.compile('/dev/sd[a-z][1-9][0-9]?$')
    try:
        return regex.match(part) is not None
    except TypeError:
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
    if iptools.validate_ip(bucket_name):
        return False
    return True


def is_valid_image_name(image_name):
    """
    Check if image_name is a valid AWS image name (as defined by the AWS docs)

    1. 3<= len(image_name) <=128
    2. all chars one of: a-z A-Z 0-9 ( ) . - / _
    """
    regex = re.compile('[\w\(\)\.\-\/_]{3,128}$')
    try:
        return regex.match(image_name) is not None
    except TypeError:
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
    return 'python -c "%s"' % script.strip().replace('\n', ';')


def is_url(url):
    """
    Returns True if the provided string is a valid url
    """
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
    """
    Returns True if provided time can be parsed in iso format
    to a datetime tuple
    """
    try:
        iso_to_datetime_tuple(iso)
        return True
    except ValueError:
        return False


def iso_to_datetime_tuple(iso):
    """
    Converts an iso time string to a datetime tuple
    """
    #remove timezone
    iso = iso.split('.')[0]
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S")
    except AttributeError:
        # python2.4 datetime module doesnt have strptime
        return datetime(*time.strptime(iso, "%Y-%m-%dT%H:%M:%S")[:6])


def datetime_tuple_to_iso(tup):
    """
    Converts a datetime tuple to iso time string
    """
    iso = datetime.strftime(tup, "%Y-%m-%dT%H:%M:%S")
    return iso


try:
    import IPython.Shell
    ipy_shell = IPython.Shell.IPShellEmbed(argv=[])
except ImportError:

    def ipy_shell():
        log.error("Unable to load IPython.")
        log.error("Please check that IPython is installed and working.")
        log.error("If not, you can install it via: easy_install ipython")


def permute(a):
    """
    Returns generator of all permutations of a

    The following code is an in-place permutation of a given list, implemented
    as a generator. Since it only returns references to the list, the list
    should not be modified outside the generator. The solution is
    non-recursive, so uses low memory. Work well also with multiple copies of
    elements in the input list.

    Retrieved from:
        http://stackoverflow.com/questions/104420/ \
        how-to-generate-all-permutations-of-a-list-in-python
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
            if a[i] < a[i + 1]:
                j = last - 1
                while not (a[i] < a[j]):
                    j = j - 1
                # swap the values
                a[i], a[j] = a[j], a[i]
                r = a[i + 1:last]
                r.reverse()
                a[i + 1:last] = r
                yield list(a)
                break
            if i == first:
                a.reverse()
                return


def has_required(programs):
    """
    Same as check_required but returns False if not all commands exist
    """
    try:
        return check_required(programs)
    except exception.CommandNotFound:
        return False


def check_required(programs):
    """
    Checks that all commands in the programs list exist. Returns
    True if all commands exist and raises exception.CommandNotFound if not.
    """
    for prog in programs:
        if not which(prog):
            raise exception.CommandNotFound(prog)
    return True


def which(program):
    """
    Returns the path to the program provided it exists and
    is on the system's PATH

    retrieved from code snippet by Jay:

    http://stackoverflow.com/questions/377017/ \
    test-if-executable-exists-in-python
    """
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file


def tailf(filename):
    """
    Constantly displays the last lines in filename
    Similar to 'tail -f' unix command
    """
    #Set the filename and open the file
    file = open(filename, 'r')

    #Find the size of the file and move to the end
    st_results = os.stat(filename)
    st_size = st_results[6]
    file.seek(st_size)

    while True:
        where = file.tell()
        line = file.readline()
        if not line:
            time.sleep(1)
            file.seek(where)
            continue
        print line,  # already has newline
