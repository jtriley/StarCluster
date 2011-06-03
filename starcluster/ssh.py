"""
ssh.py
Friendly Python SSH2 interface.
From http://commandline.org.uk/code/
License: LGPL
modified by justin riley (justin.t.riley@gmail.com)
"""

import os
import re
import sys
import stat
import string
import socket
import paramiko
import posixpath

# windows does not have termios...
try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

from starcluster import exception
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
                 port=22,
                 timeout=30):
        self._host = host
        self._port = 22
        self._pkey = None
        self._username = username or os.environ['LOGNAME']
        self._password = password
        self._timeout = timeout
        self._sftp = None
        self._transport = None
        if private_key:
            self._pkey = self.load_private_key(private_key, private_key_pass)
        elif not password:
            raise exception.SSHNoCredentialsError()

    def load_private_key(self, private_key, private_key_pass=None):
        # Use Private Key.
        log.debug('loading private key %s' % private_key)
        if private_key.endswith('rsa') or private_key.count('rsa'):
            pkey = self._load_rsa_key(private_key, private_key_pass)
        elif private_key.endswith('dsa') or private_key.count('dsa'):
            pkey = self._load_dsa_key(private_key, private_key_pass)
        else:
            log.debug("specified key does not end in either rsa or dsa" + \
                      ", trying both")
            pkey = self._load_rsa_key(private_key, private_key_pass)
            if pkey is None:
                pkey = self._load_dsa_key(private_key, private_key_pass)
        return pkey

    def connect(self, host=None, username=None, password=None,
                private_key=None, private_key_pass=None, port=22, timeout=30):
        host = host or self._host
        username = username or self._username
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
        return self

    @property
    def transport(self):
        """
        This property attempts to return an active SSH transport
        """
        if not self._transport or not self._transport.is_active():
            self.connect(self._host, self._username, self._password,
                         port=self._port, timeout=self._timeout)
        return self._transport

    def get_server_public_key(self):
        return self.transport.get_remote_server_key()

    def is_active(self):
        if self._transport:
            return self._transport.is_active()
        return False

    def _get_socket(self, hostname, port):
        for (family, socktype, proto, canonname, sockaddr) in \
        socket.getaddrinfo(hostname, port, socket.AF_UNSPEC,
                           socket.SOCK_STREAM):
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
            rsa_key = paramiko.RSAKey.from_private_key_file(private_key_file,
                                                            private_key_pass)
            log.debug("Using private key %s (rsa)" % private_key)
            return rsa_key
        except paramiko.SSHException:
            log.error('invalid rsa key or passphrase specified')

    def _load_dsa_key(self, private_key, private_key_pass=None):
        private_key_file = os.path.expanduser(private_key)
        try:
            dsa_key = paramiko.DSSKey.from_private_key_file(private_key_file,
                                                            private_key_pass)
            log.info("Using private key %s (dsa)" % private_key)
            return dsa_key
        except paramiko.SSHException:
            log.error('invalid dsa key or passphrase specified')

    @property
    def sftp(self):
        """Establish the SFTP connection."""
        if not self._sftp or self._sftp.sock.closed:
            log.debug("creating sftp connection")
            self._sftp = paramiko.SFTPClient.from_transport(self.transport)
        return self._sftp

    def generate_rsa_key(self):
        return paramiko.RSAKey.generate(2048)

    def get_public_key(self, key):
        return ' '.join([key.get_name(), key.get_base64()])

    def load_remote_rsa_key(self, remote_filename):
        """
        Returns paramiko.RSAKey object for an RSA key located on the remote
        machine
        """
        rfile = self.remote_file(remote_filename, 'r')
        key = paramiko.RSAKey(file_obj=rfile)
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
        log.debug("new %s after removing regex (%s) matches:\n%s" % \
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

    def chown(self, uid, gid, remote_file):
        """
        Apply permissions (mode) to remote_file
        """
        f = self.remote_file(remote_file, 'r')
        f.chown(uid, gid, remote_file)
        f.close()

    def chmod(self, mode, remote_file):
        """
        Apply permissions (mode) to remote_file
        """
        f = self.remote_file(remote_file, 'r')
        f.chmod(mode)
        f.close()

    def ls(self, path):
        """
        Return a list containing the names of the entries in the remote path.
        """
        return [os.path.join(path, f) for f in self.sftp.listdir(path)]

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

    def get(self, remotepath, localpath=None):
        """
        Copies a file between the remote host and the local host.
        """
        if not localpath:
            localpath = os.path.split(remotepath)[1]
        self.sftp_connect()
        self.sftp.get(remotepath, localpath)

    def put(self, localpath, remotepath=None):
        """
        Copies a file between the local host and the remote host.
        """
        if not remotepath:
            remotepath = os.path.split(localpath)[1]
        self.sftp.put(localpath, remotepath)

    def execute_async(self, command):
        """
        Executes a remote command without blocking

        NOTE: this method will not block, however, if your process does not
        complete or background itself before the python process executing this
        code exits, it will not persist on the remote machine
        """

        channel = self.transport.open_session()
        channel.exec_command(command)

    def execute(self, command, silent=True, only_printable=False,
                ignore_exit_status=False, log_output=True):
        """
        Execute a remote command and return stdout/stderr

        NOTE: this function blocks until the process finishes

        kwargs:
        silent - do not print output
        only_printable - filter the command's output to allow only printable
                        characters
        returns List of output lines
        """
        channel = self.transport.open_session()
        channel.exec_command(command)
        #stdin = channel.makefile('wb', -1)
        stdout = channel.makefile('rb', -1)
        stderr = channel.makefile_stderr('rb', -1)
        output = []
        line = None
        if silent:
            output = stdout.readlines() + stderr.readlines()
        else:
            while line != '':
                line = stdout.readline()
                if only_printable:
                    line = ''.join(c for c in line if c in string.printable)
                if line != '':
                    output.append(line)
                    print line,
            for line in stderr.readlines():
                output.append(line)
                print line
        if only_printable:
            output = map(lambda line: ''.join(c for c in line if c in
                                              string.printable), output)
        output = map(lambda line: line.strip(), output)
        exit_status = channel.recv_exit_status()
        if exit_status != 0:
            if not ignore_exit_status:
                log.error("command '%s' failed with status %d" % (command,
                                                                  exit_status))
            else:
                log.debug("command %s failed with status %d" % (command,
                                                                exit_status))
        if log_output:
            for line in output:
                log.debug(line.strip())
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

    def interactive_shell(self, user='root'):
        if user and self.transport.get_username() != user:
            self.connect(username=user)
        try:
            chan = self.transport.open_session()
            chan.get_pty()
            chan.invoke_shell()
            log.info('Starting interactive shell...')
            if HAS_TERMIOS:
                self._posix_shell(chan)
            else:
                self._windows_shell(chan)
            chan.close()
        except Exception, e:
            import traceback
            print '*** Caught exception: %s: %s' % (e.__class__, e)
            traceback.print_exc()

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

        sys.stdout.write("Line-buffered terminal emulation. " + \
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


def main():
    """Little test when called directly."""
    # Set these to your own details.
    myssh = SSHClient('somehost.domain.com')
    print myssh.execute('hostname')
    #myssh.put('ssh.py')
    myssh.close()

if __name__ == "__main__":
    main()
