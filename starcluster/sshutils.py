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
import re
import sys
import stat
import glob
import atexit
import string
import socket
import fnmatch
import hashlib
import warnings
import posixpath

import scp
import paramiko
from Crypto.PublicKey import RSA
from Crypto.PublicKey import DSA

# windows does not have termios...
try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

from starcluster import exception
from starcluster import progressbar
from starcluster.logger import log


class SSHClient(object):
    """
    Establishes an SSH connection to a remote host using either password or
    private key authentication. Once established, this object allows executing
    commands, copying files to/from the remote host, various file querying
    similar to os.path.*, and much more.
    """

    def __init__(self,
                 host,
                 username=None,
                 password=None,
                 private_key=None,
                 private_key_pass=None,
                 compress=False,
                 port=22,
                 timeout=30):
        self._host = host
        self._port = port
        self._pkey = None
        self._username = username or os.environ['LOGNAME']
        self._password = password
        self._timeout = timeout
        self._sftp = None
        self._scp = None
        self._transport = None
        self._progress_bar = None
        self._compress = compress
        if private_key:
            self._pkey = self.load_private_key(private_key, private_key_pass)
        elif not password:
            raise exception.SSHNoCredentialsError()
        self._glob = SSHGlob(self)
        self.__last_status = None
        atexit.register(self.close)

    def load_private_key(self, private_key, private_key_pass=None):
        # Use Private Key.
        log.debug('loading private key %s' % private_key)
        if private_key.endswith('rsa') or private_key.count('rsa'):
            pkey = self._load_rsa_key(private_key, private_key_pass)
        elif private_key.endswith('dsa') or private_key.count('dsa'):
            pkey = self._load_dsa_key(private_key, private_key_pass)
        else:
            log.debug(
                "specified key does not end in either rsa or dsa, trying both")
            pkey = self._load_rsa_key(private_key, private_key_pass)
            if pkey is None:
                pkey = self._load_dsa_key(private_key, private_key_pass)
        return pkey

    def connect(self, host=None, username=None, password=None,
                private_key=None, private_key_pass=None, port=None, timeout=30,
                compress=None):
        host = host or self._host
        username = username or self._username
        password = password or self._password
        compress = compress or self._compress
        port = port if port is not None else self._port
        pkey = self._pkey
        if private_key:
            pkey = self.load_private_key(private_key, private_key_pass)
        log.debug("connecting to host %s on port %d as user %s" % (host, port,
                                                                   username))
        try:
            sock = self._get_socket(host, port)
            transport = paramiko.Transport(sock)
            transport.banner_timeout = timeout
        except socket.error:
            raise exception.SSHConnectionError(host, port)
        # Enable/disable compression
        transport.use_compression(compress)
        # Authenticate the transport.
        try:
            transport.connect(username=username, pkey=pkey, password=password)
        except paramiko.AuthenticationException:
            raise exception.SSHAuthException(username, host)
        except paramiko.SSHException, e:
            msg = e.args[0]
            raise exception.SSHError(msg)
        except socket.error:
            raise exception.SSHConnectionError(host, port)
        except EOFError:
            raise exception.SSHConnectionError(host, port)
        except Exception, e:
            raise exception.SSHError(str(e))
        self.close()
        self._transport = transport
        try:
            assert self.sftp is not None
        except paramiko.SFTPError, e:
            if 'Garbage packet received' in e:
                log.debug("Garbage packet received", exc_info=True)
                raise exception.SSHAccessDeniedViaAuthKeys(username)
            raise
        return self

    @property
    def transport(self):
        """
        This property attempts to return an active SSH transport
        """
        if not self._transport or not self._transport.is_active():
            self.connect(self._host, self._username, self._password,
                         port=self._port, timeout=self._timeout,
                         compress=self._compress)
        return self._transport

    def get_server_public_key(self):
        return self.transport.get_remote_server_key()

    def is_active(self):
        if self._transport:
            return self._transport.is_active()
        return False

    def _get_socket(self, hostname, port):
        addrinfo = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC,
                                      socket.SOCK_STREAM)
        for (family, socktype, proto, canonname, sockaddr) in addrinfo:
            if socktype == socket.SOCK_STREAM:
                af = family
                break
            else:
                raise exception.SSHError(
                    'No suitable address family for %s' % hostname)
        sock = socket.socket(af, socket.SOCK_STREAM)
        sock.settimeout(self._timeout)
        sock.connect((hostname, port))
        return sock

    def _load_rsa_key(self, private_key, private_key_pass=None):
        private_key_file = os.path.expanduser(private_key)
        try:
            rsa_key = get_rsa_key(key_location=private_key_file,
                                  passphrase=private_key_pass)
            log.debug("Using private key %s (RSA)" % private_key)
            return rsa_key
        except (paramiko.SSHException, exception.SSHError):
            log.error('invalid rsa key or passphrase specified')

    def _load_dsa_key(self, private_key, private_key_pass=None):
        private_key_file = os.path.expanduser(private_key)
        try:
            dsa_key = get_dsa_key(key_location=private_key_file,
                                  passphrase=private_key_pass)
            log.info("Using private key %s (DSA)" % private_key)
            return dsa_key
        except (paramiko.SSHException, exception.SSHError):
            log.error('invalid dsa key or passphrase specified')

    @property
    def sftp(self):
        """Establish the SFTP connection."""
        if not self._sftp or self._sftp.sock.closed:
            log.debug("creating sftp connection")
            self._sftp = paramiko.SFTPClient.from_transport(self.transport)
        return self._sftp

    @property
    def scp(self):
        """Initialize the SCP client."""
        if not self._scp or not self._scp.transport.is_active():
            log.debug("creating scp connection")
            self._scp = scp.SCPClient(self.transport,
                                      progress=self._file_transfer_progress,
                                      socket_timeout=self._timeout)
        return self._scp

    def generate_rsa_key(self):
        warnings.warn("This method is deprecated: please use "
                      "starcluster.sshutils.generate_rsa_key instead")
        return generate_rsa_key()

    def get_public_key(self, key):
        warnings.warn("This method is deprecated: please use "
                      "starcluster.sshutils.get_public_key instead")
        return get_public_key(key)

    def load_remote_rsa_key(self, remote_filename):
        """
        Returns paramiko.RSAKey object for an RSA key located on the remote
        machine
        """
        rfile = self.remote_file(remote_filename, 'r')
        key = get_rsa_key(key_file_obj=rfile)
        rfile.close()
        return key

    def makedirs(self, path, mode=0755):
        """
        Same as os.makedirs - makes a new directory and automatically creates
        all parent directories if they do not exist.

        mode specifies unix permissions to apply to the new dir
        """
        head, tail = posixpath.split(path)
        if not tail:
            head, tail = posixpath.split(head)
        if head and tail and not self.path_exists(head):
            try:
                self.makedirs(head, mode)
            except OSError, e:
                # be happy if someone already created the path
                if e.errno != os.errno.EEXIST:
                    raise
            # xxx/newdir/. exists if xxx/newdir exists
            if tail == posixpath.curdir:
                return
        self.mkdir(path, mode)

    def mkdir(self, path, mode=0755, ignore_failure=False):
        """
        Make a new directory on the remote machine

        If parent is True, create all parent directories that do not exist

        mode specifies unix permissions to apply to the new dir
        """
        try:
            return self.sftp.mkdir(path, mode)
        except IOError:
            if not ignore_failure:
                raise

    def get_remote_file_lines(self, remote_file, regex=None, matching=True):
        """
        Returns list of lines in a remote_file

        If regex is passed only lines that contain a pattern that matches
        regex will be returned

        If matching is set to False then only lines *not* containing a pattern
        that matches regex will be returned
        """
        f = self.remote_file(remote_file, 'r')
        flines = f.readlines()
        f.close()
        if regex is None:
            return flines
        r = re.compile(regex)
        lines = []
        for line in flines:
            match = r.search(line)
            if matching and match:
                lines.append(line)
            elif not matching and not match:
                lines.append(line)
        return lines

    def remove_lines_from_file(self, remote_file, regex):
        """
        Removes lines matching regex from remote_file
        """
        if regex in [None, '']:
            log.debug('no regex supplied...returning')
            return
        lines = self.get_remote_file_lines(remote_file, regex, matching=False)
        log.debug("new %s after removing regex (%s) matches:\n%s" %
                  (remote_file, regex, ''.join(lines)))
        f = self.remote_file(remote_file)
        f.writelines(lines)
        f.close()

    def unlink(self, remote_file):
        return self.sftp.unlink(remote_file)

    def remote_file(self, file, mode='w'):
        """
        Returns a remote file descriptor
        """
        rfile = self.sftp.open(file, mode)
        rfile.name = file
        return rfile

    def path_exists(self, path):
        """
        Test whether a remote path exists.
        Returns False for broken symbolic links
        """
        try:
            self.stat(path)
            return True
        except IOError:
            return False

    def lpath_exists(self, path):
        """
        Test whether a remote path exists.
        Returns True for broken symbolic links
        """
        try:
            self.lstat(path)
            return True
        except IOError:
            return False

    def chown(self, uid, gid, remote_path):
        """
        Set user (uid) and group (gid) owner for remote_path
        """
        return self.sftp.chown(remote_path, uid, gid)

    def chmod(self, mode, remote_path):
        """
        Apply permissions (mode) to remote_path
        """
        return self.sftp.chmod(remote_path, mode)

    def ls(self, path):
        """
        Return a list containing the names of the entries in the remote path.
        """
        return [posixpath.join(path, f) for f in self.sftp.listdir(path)]

    def glob(self, pattern):
        return self._glob.glob(pattern)

    def isdir(self, path):
        """
        Return true if the remote path refers to an existing directory.
        """
        try:
            s = self.stat(path)
        except IOError:
            return False
        return stat.S_ISDIR(s.st_mode)

    def isfile(self, path):
        """
        Return true if the remote path refers to an existing file.
        """
        try:
            s = self.stat(path)
        except IOError:
            return False
        return stat.S_ISREG(s.st_mode)

    def stat(self, path):
        """
        Perform a stat system call on the given remote path.
        """
        return self.sftp.stat(path)

    def lstat(self, path):
        """
        Same as stat but doesn't follow symlinks
        """
        return self.sftp.lstat(path)

    @property
    def progress_bar(self):
        if not self._progress_bar:
            widgets = ['FileTransfer: ', ' ', progressbar.Percentage(), ' ',
                       progressbar.Bar(marker=progressbar.RotatingMarker()),
                       ' ', progressbar.ETA(), ' ',
                       progressbar.FileTransferSpeed()]
            pbar = progressbar.ProgressBar(widgets=widgets,
                                           maxval=1,
                                           force_update=True)
            self._progress_bar = pbar
        return self._progress_bar

    def _file_transfer_progress(self, filename, size, sent):
        pbar = self.progress_bar
        pbar.widgets[0] = filename
        pbar.maxval = size
        pbar.update(sent)
        if pbar.finished:
            pbar.reset()

    def _make_list(self, obj):
        if not isinstance(obj, (list, tuple)):
            return [obj]
        return obj

    def get(self, remotepaths, localpath=''):
        """
        Copies one or more files from the remote host to the local host.
        """
        remotepaths = self._make_list(remotepaths)
        localpath = localpath or os.getcwd()
        globs = []
        noglobs = []
        for rpath in remotepaths:
            if glob.has_magic(rpath):
                globs.append(rpath)
            else:
                noglobs.append(rpath)
        globresults = [self.glob(g) for g in globs]
        remotepaths = noglobs
        for globresult in globresults:
            remotepaths.extend(globresult)
        recursive = False
        for rpath in remotepaths:
            if not self.path_exists(rpath):
                raise exception.BaseException(
                    "Remote file or directory does not exist: %s" % rpath)
        for rpath in remotepaths:
            if self.isdir(rpath):
                recursive = True
                break
        try:
            self.scp.get(remotepaths, local_path=localpath,
                         recursive=recursive)
        except Exception, e:
            log.debug("get failed: remotepaths=%s, localpath=%s",
                      str(remotepaths), localpath)
            raise exception.SCPException(str(e))

    def put(self, localpaths, remotepath='.'):
        """
        Copies one or more files from the local host to the remote host.
        """
        localpaths = self._make_list(localpaths)
        recursive = False
        for lpath in localpaths:
            if os.path.isdir(lpath):
                recursive = True
                break
        try:
            self.scp.put(localpaths, remote_path=remotepath,
                         recursive=recursive)
        except Exception, e:
            log.debug("put failed: localpaths=%s, remotepath=%s",
                      str(localpaths), remotepath)
            raise exception.SCPException(str(e))

    def execute_async(self, command, source_profile=True):
        """
        Executes a remote command so that it continues running even after this
        SSH connection closes. The remote process will be put into the
        background via nohup. Does not return output or check for non-zero exit
        status.
        """
        return self.execute(command, detach=True,
                            source_profile=source_profile)

    def get_last_status(self):
        return self.__last_status

    def get_status(self, command, source_profile=True):
        """
        Execute a remote command and return the exit status
        """
        channel = self.transport.open_session()
        if source_profile:
            command = "source /etc/profile && %s" % command
        channel.exec_command(command)
        self.__last_status = channel.recv_exit_status()
        return self.__last_status

    def _get_output(self, channel, silent=True, only_printable=False):
        """
        Returns the stdout/stderr output from a ssh channel as a list of
        strings (non-interactive only)
        """
        # stdin = channel.makefile('wb', -1)
        stdout = channel.makefile('rb', -1)
        stderr = channel.makefile_stderr('rb', -1)
        if silent:
            output = stdout.readlines() + stderr.readlines()
        else:
            output = []
            line = None
            while line != '':
                line = stdout.readline()
                if only_printable:
                    line = ''.join(c for c in line if c in string.printable)
                if line != '':
                    output.append(line)
                    print line,
            for line in stderr.readlines():
                output.append(line)
                print line,
        if only_printable:
            output = map(lambda line: ''.join(c for c in line if c in
                                              string.printable), output)
        output = map(lambda line: line.strip(), output)
        return output

    def execute(self, command, silent=True, only_printable=False,
                ignore_exit_status=False, log_output=True, detach=False,
                source_profile=True, raise_on_failure=True):
        """
        Execute a remote command and return stdout/stderr

        NOTE: this function blocks until the process finishes

        kwargs:
        silent - don't print the command's output to the console
        only_printable - filter the command's output to allow only printable
                         characters
        ignore_exit_status - don't warn about non-zero exit status
        log_output - log all remote output to the debug file
        detach - detach the remote process so that it continues to run even
                 after the SSH connection closes (does NOT return output or
                 check for non-zero exit status if detach=True)
        source_profile - if True prefix the command with "source /etc/profile"
        raise_on_failure - raise exception.SSHError if command fails
        returns List of output lines
        """
        channel = self.transport.open_session()
        if detach:
            command = "nohup %s &" % command
            if source_profile:
                command = "source /etc/profile && %s" % command
            channel.exec_command(command)
            channel.close()
            self.__last_status = None
            return
        if source_profile:
            command = "source /etc/profile && %s" % command
        log.debug("executing remote command: %s" % command)
        channel.exec_command(command)
        output = self._get_output(channel, silent=silent,
                                  only_printable=only_printable)
        exit_status = channel.recv_exit_status()
        self.__last_status = exit_status
        out_str = '\n'.join(output)
        if exit_status != 0:
            msg = "remote command '%s' failed with status %d"
            msg %= (command, exit_status)
            if log_output:
                msg += ":\n%s" % out_str
            else:
                msg += " (no output log requested)"
            if not ignore_exit_status:
                if raise_on_failure:
                    raise exception.RemoteCommandFailed(
                        msg, command, exit_status, out_str)
                else:
                    log.error(msg)
            else:
                log.debug("(ignored) " + msg)
        else:
            if log_output:
                log.debug("output of '%s':\n%s" % (command, out_str))
            else:
                log.debug("output of '%s' has been hidden" % command)
        return output

    def has_required(self, progs):
        """
        Same as check_required but returns False if not all commands exist
        """
        try:
            return self.check_required(progs)
        except exception.RemoteCommandNotFound:
            return False

    def check_required(self, progs):
        """
        Checks that all commands in the progs list exist on the remote system.
        Returns True if all commands exist and raises exception.CommandNotFound
        if not.
        """
        for prog in progs:
            if not self.which(prog):
                raise exception.RemoteCommandNotFound(prog)
        return True

    def which(self, prog):
        return self.execute('which %s' % prog, ignore_exit_status=True)

    def get_path(self):
        """Returns the PATH environment variable on the remote machine"""
        return self.get_env()['PATH']

    def get_env(self):
        """Returns the remote machine's environment as a dictionary"""
        env = {}
        for line in self.execute('env'):
            key, val = line.split('=', 1)
            env[key] = val
        return env

    def close(self):
        """Closes the connection and cleans up."""
        if self._sftp:
            self._sftp.close()
        if self._transport:
            self._transport.close()

    def _invoke_shell(self, term='screen', cols=80, lines=24):
        chan = self.transport.open_session()
        chan.get_pty(term, cols, lines)
        chan.invoke_shell()
        return chan

    def get_current_user(self):
        if not self.is_active():
            return
        return self.transport.get_username()

    def switch_user(self, user):
        """
        Reconnect, if necessary, to host as user
        """
        if not self.is_active() or user and self.get_current_user() != user:
            self.connect(username=user)
        else:
            user = user or self._username
            log.debug("already connected as user %s" % user)

    def interactive_shell(self, user='root'):
        orig_user = self.get_current_user()
        self.switch_user(user)
        chan = self._invoke_shell()
        log.info('Starting Pure-Python SSH shell...')
        if HAS_TERMIOS:
            self._posix_shell(chan)
        else:
            self._windows_shell(chan)
        chan.close()
        self.switch_user(orig_user)

    def _posix_shell(self, chan):
        import select

        oldtty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            chan.settimeout(0.0)

            # needs to be sent to give vim correct size FIX
            chan.send('eval $(resize)\n')

            while True:
                r, w, e = select.select([chan, sys.stdin], [], [])
                if chan in r:
                    try:
                        x = chan.recv(1024)
                        if len(x) == 0:
                            print '\r\n*** EOF\r\n',
                            break
                        sys.stdout.write(x)
                        sys.stdout.flush()
                    except socket.timeout:
                        pass
                if sys.stdin in r:
                    # fixes up arrow problem
                    x = os.read(sys.stdin.fileno(), 1)
                    if len(x) == 0:
                        break
                    chan.send(x)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

    # thanks to Mike Looijmans for this code
    def _windows_shell(self, chan):
        import threading

        sys.stdout.write("Line-buffered terminal emulation. "
                         "Press F6 or ^Z to send EOF.\r\n\r\n")

        def writeall(sock):
            while True:
                data = sock.recv(256)
                if not data:
                    sys.stdout.write('\r\n*** EOF ***\r\n\r\n')
                    sys.stdout.flush()
                    break
                sys.stdout.write(data)
                sys.stdout.flush()

        writer = threading.Thread(target=writeall, args=(chan,))
        writer.start()

        # needs to be sent to give vim correct size FIX
        chan.send('eval $(resize)\n')

        try:
            while True:
                d = sys.stdin.read(1)
                if not d:
                    break
                chan.send(d)
        except EOFError:
            # user hit ^Z or F6
            pass

    def __del__(self):
        """Attempt to clean up if not explicitly closed."""
        log.debug('__del__ called')
        self.close()


# for backwards compatibility
Connection = SSHClient


class SSHGlob(object):

    def __init__(self, ssh_client):
        self.ssh = ssh_client

    def glob(self, pathname):
        return list(self.iglob(pathname))

    def iglob(self, pathname):
        """
        Return an iterator which yields the paths matching a pathname pattern.
        The pattern may contain simple shell-style wildcards a la fnmatch.
        """
        if not glob.has_magic(pathname):
            if self.ssh.lpath_exists(pathname):
                yield pathname
            return
        dirname, basename = posixpath.split(pathname)
        if not dirname:
            for name in self.glob1(posixpath.curdir, basename):
                yield name
            return
        if glob.has_magic(dirname):
            dirs = self.iglob(dirname)
        else:
            dirs = [dirname]
        if glob.has_magic(basename):
            glob_in_dir = self.glob1
        else:
            glob_in_dir = self.glob0
        for dirname in dirs:
            for name in glob_in_dir(dirname, basename):
                yield posixpath.join(dirname, name)

    def glob0(self, dirname, basename):
        if basename == '':
            # `os.path.split()` returns an empty basename for paths ending with
            # a directory separator.  'q*x/' should match only directories.
            if self.ssh.isdir(dirname):
                return [basename]
        else:
            if self.ssh.lexists(posixpath.join(dirname, basename)):
                return [basename]
        return []

    def glob1(self, dirname, pattern):
        if not dirname:
            dirname = posixpath.curdir
        if isinstance(pattern, unicode) and not isinstance(dirname, unicode):
            # enc = sys.getfilesystemencoding() or sys.getdefaultencoding()
            # dirname = unicode(dirname, enc)
            dirname = unicode(dirname, 'UTF-8')
        try:
            names = [posixpath.basename(n) for n in self.ssh.ls(dirname)]
        except os.error:
            return []
        if pattern[0] != '.':
            names = filter(lambda x: x[0] != '.', names)
        return fnmatch.filter(names, pattern)


def insert_char_every_n_chars(string, char='\n', every=64):
    return char.join(
        string[i:i + every] for i in xrange(0, len(string), every))


def get_rsa_key(key_location=None, key_file_obj=None, passphrase=None,
                use_pycrypto=False):
    key_fobj = key_file_obj or open(key_location)
    try:
        if use_pycrypto:
            key = RSA.importKey(key_fobj, passphrase=passphrase)
        else:
            key = paramiko.RSAKey.from_private_key(key_fobj,
                                                   password=passphrase)
        return key
    except (paramiko.SSHException, ValueError):
        raise exception.SSHError(
            "Invalid RSA private key file or missing passphrase: %s" %
            key_location)


def get_dsa_key(key_location=None, key_file_obj=None, passphrase=None,
                use_pycrypto=False):
    key_fobj = key_file_obj or open(key_location)
    try:
        key = paramiko.DSSKey.from_private_key(key_fobj,
                                               password=passphrase)
        if use_pycrypto:
            key = DSA.construct((key.y, key.g, key.p, key.q, key.x))
        return key
    except (paramiko.SSHException, ValueError):
        raise exception.SSHError(
            "Invalid DSA private key file or missing passphrase: %s" %
            key_location)


def get_public_key(key):
    return ' '.join([key.get_name(), key.get_base64()])


def generate_rsa_key():
    return paramiko.RSAKey.generate(2048)


def get_private_rsa_fingerprint(key_location=None, key_file_obj=None,
                                passphrase=None):
    """
    Returns the fingerprint of a private RSA key as a 59-character string (40
    characters separated every 2 characters by a ':'). The fingerprint is
    computed using the SHA1 (hex) digest of the DER-encoded (pkcs8) RSA private
    key.
    """
    k = get_rsa_key(key_location=key_location, key_file_obj=key_file_obj,
                    passphrase=passphrase, use_pycrypto=True)
    sha1digest = hashlib.sha1(k.exportKey('DER', pkcs=8)).hexdigest()
    fingerprint = insert_char_every_n_chars(sha1digest, ':', 2)
    key = key_location or key_file_obj
    log.debug("rsa private key fingerprint (%s): %s" % (key, fingerprint))
    return fingerprint


def get_public_rsa_fingerprint(key_location=None, key_file_obj=None,
                               passphrase=None):
    """
    Returns the fingerprint of the public portion of an RSA key as a
    47-character string (32 characters separated every 2 characters by a ':').
    The fingerprint is computed using the MD5 (hex) digest of the DER-encoded
    RSA public key.
    """
    privkey = get_rsa_key(key_location=key_location, key_file_obj=key_file_obj,
                          passphrase=passphrase, use_pycrypto=True)
    pubkey = privkey.publickey()
    md5digest = hashlib.md5(pubkey.exportKey('DER')).hexdigest()
    fingerprint = insert_char_every_n_chars(md5digest, ':', 2)
    key = key_location or key_file_obj
    log.debug("rsa public key fingerprint (%s): %s" % (key, fingerprint))
    return fingerprint


def test_create_keypair_fingerprint(keypair=None):
    """
    TODO: move this to 'live' tests
    """
    from starcluster import config
    cfg = config.StarClusterConfig().load()
    ec2 = cfg.get_easy_ec2()
    if keypair is None:
        keypair = cfg.keys.keys()[0]
    key_location = cfg.get_key(keypair).key_location
    localfprint = get_private_rsa_fingerprint(key_location)
    ec2fprint = ec2.get_keypair(keypair).fingerprint
    print 'local fingerprint: %s' % localfprint
    print '  ec2 fingerprint: %s' % ec2fprint
    assert localfprint == ec2fprint


def test_import_keypair_fingerprint(keypair):
    """
    TODO: move this to 'live' tests
    """
    from starcluster import config
    cfg = config.StarClusterConfig().load()
    ec2 = cfg.get_easy_ec2()
    key_location = cfg.get_key(keypair).key_location
    localfprint = get_public_rsa_fingerprint(key_location)
    ec2fprint = ec2.get_keypair(keypair).fingerprint
    print 'local fingerprint: %s' % localfprint
    print '  ec2 fingerprint: %s' % ec2fprint
    assert localfprint == ec2fprint
