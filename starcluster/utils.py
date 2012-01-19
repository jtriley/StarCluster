"""
Utils module for StarCluster
"""

import os
import re
import time
import types
import string
import random
import inspect
import calendar
import urlparse
import decorator
from datetime import datetime

from starcluster import iptools
from starcluster import exception
from starcluster.logger import log

try:
    import IPython
    if IPython.__version__ < '0.11':
        from IPython.Shell import IPShellEmbed
        ipy_shell = IPShellEmbed(argv=[])
    else:
        from IPython import embed
        ipy_shell = lambda local_ns=None: embed(user_ns=local_ns)
except ImportError, e:

    def ipy_shell(local_ns=None):
        log.error("Unable to load IPython:\n\n%s\n" % e)
        log.error("Please check that IPython is installed and working.")
        log.error("If not, you can install it via: easy_install ipython")

try:
    import pudb
    set_trace = pudb.set_trace
except ImportError:

    def set_trace():
        log.error("Unable to load PuDB")
        log.error("Please check that PuDB is installed and working.")
        log.error("If not, you can install it via: easy_install pudb")


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
        print 'Running myfunc'
    >>> myfunc()
    Running myfunc
    myfunc took 0.000 mins

    @print_timing('My function')
    def myfunc():
        print 'Running myfunc'
    >>> myfunc()
    Running myfunc
    My function took 0.000 mins
    """
    prefix = msg
    if type(msg) == types.FunctionType:
        prefix = msg.func_name

    def wrap_f(func, *arg, **kargs):
        """Raw timing function """
        time1 = time.time()
        res = func(*arg, **kargs)
        time2 = time.time()
        log.info('%s took %0.3f mins' % (prefix, (time2 - time1) / 60.0))
        return res

    if type(msg) == types.FunctionType:
        return decorator.decorator(wrap_f, msg)
    else:
        return decorator.decorator(wrap_f)


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


def get_elapsed_time(past_time):
    ptime = iso_to_localtime_tuple(past_time)
    now = datetime.now()
    delta = now - ptime
    timestr = time.strftime("%H:%M:%S", time.gmtime(delta.seconds))
    if delta.days != -1:
        timestr = "%d days, %s" % (delta.days, timestr)
    return timestr


def iso_to_unix_time(iso):
    dtup = iso_to_datetime_tuple(iso)
    secs = calendar.timegm(dtup.timetuple())
    return secs


def iso_to_javascript_timestamp(iso):
    """
    Convert dates to Javascript timestamps (number of milliseconds since
    January 1st 1970 UTC)
    """
    secs = iso_to_unix_time(iso)
    return secs * 1000


def iso_to_localtime_tuple(iso):
    secs = iso_to_unix_time(iso)
    t = time.mktime(time.localtime(secs))
    return datetime.fromtimestamp(t)


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


def v2fhelper(v, suff, version, weight):
    parts = v.split(suff)
    if 2 != len(parts):
        return v
    version[4] = weight
    version[5] = parts[1]
    return parts[0]


def version_to_float(v):
    # This code was written by Krzysztof Kowalczyk (http://blog.kowalczyk.info)
    # and is placed in public domain.
    """
    Convert a Mozilla-style version string into a floating-point number
    1.2.3.4, 1.2a5, 2.3.4b1pre, 3.0rc2, etc.
    """
    version = [
        0, 0, 0, 0,  # 4-part numerical revision
        4,  # Alpha, beta, RC or (default) final
        0,  # Alpha, beta, or RC version revision
        1   # Pre or (default) final
    ]
    parts = v.split("pre")
    if 2 == len(parts):
        version[6] = 0
        v = parts[0]

    v = v2fhelper(v, "a",  version, 1)
    v = v2fhelper(v, "b",  version, 2)
    v = v2fhelper(v, "rc", version, 3)

    parts = v.split(".")[:4]
    for (p, i) in zip(parts, range(len(parts))):
        version[i] = p
    ver = float(version[0])
    ver += float(version[1]) / 100.
    ver += float(version[2]) / 10000.
    ver += float(version[3]) / 1000000.
    ver += float(version[4]) / 100000000.
    ver += float(version[5]) / 10000000000.
    ver += float(version[6]) / 1000000000000.
    return ver


def program_version_greater(ver1, ver2):
    """
    Return True if ver1 > ver2 using semantics of comparing version
    numbers
    """
    v1f = version_to_float(ver1)
    v2f = version_to_float(ver2)
    return v1f > v2f


def test_version_to_float():
    assert program_version_greater("1", "0.9")
    assert program_version_greater("0.0.0.2", "0.0.0.1")
    assert program_version_greater("1.0", "0.9")
    assert program_version_greater("2.0.1", "2.0.0")
    assert program_version_greater("2.0.1", "2.0")
    assert program_version_greater("2.0.1", "2")
    assert program_version_greater("0.9.1", "0.9.0")
    assert program_version_greater("0.9.2", "0.9.1")
    assert program_version_greater("0.9.11", "0.9.2")
    assert program_version_greater("0.9.12", "0.9.11")
    assert program_version_greater("0.10", "0.9")
    assert program_version_greater("2.0", "2.0b35")
    assert program_version_greater("1.10.3", "1.10.3b3")
    assert program_version_greater("88", "88a12")
    assert program_version_greater("0.0.33", "0.0.33rc23")
    assert program_version_greater("0.91.2", "0.91.1")
    assert program_version_greater("0.9999", "0.91.1")
    assert program_version_greater("0.9999", "0.92")
    assert program_version_greater("0.91.10", "0.91.1")
    assert program_version_greater("0.92", "0.91.11")
    assert program_version_greater("0.92", "0.92b1")
    assert program_version_greater("0.9999", "0.92b3")
    print("All tests passed")


def get_arg_spec(func):
    """
    Convenience wrapper around inspect.getargspec

    Returns a tuple whose first element is a list containing the names of all
    required arguments and whose second element is a list containing the names
    of all keyword (optional) arguments.
    """
    allargs, varargs, keywords, defaults = inspect.getargspec(func)
    if 'self' in allargs:
        allargs.remove('self')  # ignore self
    nargs = len(allargs)
    ndefaults = 0
    if defaults:
        ndefaults = len(defaults)
    nrequired = nargs - ndefaults
    args = allargs[:nrequired]
    kwargs = allargs[nrequired:]
    log.debug('nargs = %s' % nargs)
    log.debug('ndefaults = %s' % ndefaults)
    log.debug('nrequired = %s' % nrequired)
    log.debug('args = %s' % args)
    log.debug('kwargs = %s' % kwargs)
    log.debug('defaults = %s' % str(defaults))
    return args, kwargs


def chunk_list(ls, items=8):
    """
    iterate through 'chunks' of a list. final chunk consists of remaining
    elements if items does not divide len(ls) evenly.

    items - size of 'chunks'
    """
    itms = []
    for i, v in enumerate(ls):
        if i >= items and i % items == 0:
            yield itms
            itms = [v]
        else:
            itms.append(v)
    if itms:
        yield itms


def generate_passwd(length):
    return "".join(random.sample(string.letters + string.digits, length))


class struct_group(tuple):
    """
    grp.struct_group: Results from getgr*() routines.

    This object may be accessed either as a tuple of
      (gr_name,gr_passwd,gr_gid,gr_mem)
    or via the object attributes as named in the above tuple.
    """

    attrs = ['gr_name', 'gr_passwd', 'gr_gid', 'gr_mem']

    def __new__(cls, grp):
        if type(grp) not in (list, str, tuple):
            grp = (grp.name, grp.password, int(grp.GID),
                   [member for member in grp.members])
        if len(grp) != 4:
            raise TypeError('expecting a 4-sequence (%d-sequence given)' %
                            len(grp))
        return tuple.__new__(cls, grp)

    def __getattr__(self, attr):
        try:
            return self[self.attrs.index(attr)]
        except ValueError:
            raise AttributeError


class struct_passwd(tuple):
    """
    pwd.struct_passwd: Results from getpw*() routines.

    This object may be accessed either as a tuple of
      (pw_name,pw_passwd,pw_uid,pw_gid,pw_gecos,pw_dir,pw_shell)
    or via the object attributes as named in the above tuple.
    """

    attrs = ['pw_name', 'pw_passwd', 'pw_uid', 'pw_gid', 'pw_gecos',
             'pw_dir', 'pw_shell']

    def __new__(cls, pwd):
        if type(pwd) not in (list, str, tuple):
            pwd = (pwd.loginName, pwd.password, int(pwd.UID), int(pwd.GID),
                   pwd.GECOS, pwd.home, pwd.shell)
        if len(pwd) != 7:
            raise TypeError('expecting a 4-sequence (%d-sequence given)' %
                            len(pwd))
        return tuple.__new__(cls, pwd)

    def __getattr__(self, attr):
        try:
            return self[self.attrs.index(attr)]
        except ValueError:
            raise AttributeError
