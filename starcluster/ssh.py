"""
ssh.py
Friendly Python SSH2 interface.
From http://commandline.org.uk/code/
License: LGPL
modified by justin riley (justin.t.riley@gmail.com)
"""

import os
import tempfile
import paramiko
import logging


log = logging.getLogger('starcluster')

class Connection(object):
    """Connects and logs into the specified hostname. 
    Arguments that are not given are guessed from the environment.""" 

    def __init__(self,
                 host,
                 username = None,
                 password = None,
                 private_key = None,
                 private_key_pass = None,
                 port = 22,
                 ):
        self._sftp_live = False
        self._sftp = None
        if not username:
            username = os.environ['LOGNAME']

        # Log to a temporary file.
        templog = tempfile.mkstemp('.txt', 'ssh-')[1]
        paramiko.util.log_to_file(templog)

        # Begin the SSH transport.
        self._transport = paramiko.Transport((host, port))
        self._tranport_live = True
        # Authenticate the transport.
        if password:
            # Using Password.
            self._transport.connect(username = username, password = password)
        else:
            # Use Private Key.
            pkey = None
            if private_key:
                log.debug('private key specified')
                if private_key.endswith('rsa'):
                    pkey = self._load_rsa_key(private_key, private_key_pass)
                elif private_key.endswith('dsa'):
                    pkey = self._load_dsa_key(private_key, private_key_pass)
                else:
                    log.warn("specified key does not end in either rsa or dsa, trying both")
                    pkey = self._load_rsa_key(private_key, private_key_pass)
                    if pkey is None:
                        pkey = self._load_dsa_key(private_key, private_key_pass)
            else:
                log.debug('no private_key specified')
                # Try to use default key.
                if os.path.exists(os.path.expanduser('~/.ssh/id_rsa')):
                    pkey = self._load_rsa_key('~/.ssh/id_rsa')
                elif os.path.exists(os.path.expanduser('~/.ssh/id_dsa')):
                    pkey = self._load_dsa_key('~/.ssh/id_dsa')
                else:
                    raise TypeError, "You have not specified a password or key."

            self._transport.connect(username = username, pkey = pkey)

    def _load_rsa_key(self, private_key, private_key_pass=None):
        private_key_file = os.path.expanduser(private_key)
        try:
            rsa_key = paramiko.RSAKey.from_private_key_file(private_key_file, private_key_pass)
            return rsa_key
        except paramiko.SSHException,e:
            log.error('invalid rsa key or password specified')

    def _load_dsa_key(self, private_key, private_key_pass=None):
        private_key_file = os.path.expanduser(private_key)
        try:
            dsa_key = paramiko.DSSKey.from_private_key_file(private_key_file, private_key_pass)
            return dsa_key
        except paramiko.SSHException,e:
            log.error('invalid dsa key or password specified')
    
    def _sftp_connect(self):
        """Establish the SFTP connection."""
        if not self._sftp_live:
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            self._sftp_live = True

    def remote_file(self, file, mode='w'):
        """Returns a remote file descriptor"""
        self._sftp_connect()
        rfile = self._sftp.open(file, mode)
        rfile.name=file
        return rfile

    def get(self, remotepath, localpath = None):
        """Copies a file between the remote host and the local host."""
        if not localpath:
            localpath = os.path.split(remotepath)[1]
        self._sftp_connect()
        self._sftp.get(remotepath, localpath)

    def put(self, localpath, remotepath = None):
        """Copies a file between the local host and the remote host."""
        if not remotepath:
            remotepath = os.path.split(localpath)[1]
        self._sftp_connect()
        self._sftp.put(localpath, remotepath)

    def execute(self, command, silent = True):
        """Execute the given commands on a remote machine."""
        channel = self._transport.open_session()
        channel.exec_command(command)
        stdout = channel.makefile('rb', -1).readlines()
        stderr = channel.makefile_stderr('rb', -1).readlines()
        output = stdout+stderr
        output = [ line.strip() for line in output ]

        if not silent:
            for line in output:
                print line
        else:
            for line in output:
                log.debug(line.strip())
        return output

    def close(self):
        """Closes the connection and cleans up."""
        # Close SFTP Connection.
        if self._sftp_live:
            self._sftp.close()
            self._sftp_live = False
        # Close the SSH Transport.
        if self._tranport_live:
            self._transport.close()
            self._tranport_live = False

    def __del__(self):
        """Attempt to clean up if not explicitly closed."""
        log.debug('__del__ called')
        self.close()

def main():
    """Little test when called directly."""
    # Set these to your own details.
    myssh = Connection('example.com')
    myssh.put('ssh.py')
    myssh.close()

# start the ball rolling.
if __name__ == "__main__":
    main()
