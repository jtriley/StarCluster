##########################
Frequently Asked Questions
##########################
Below are the answers to some frequently asked questions on the StarCluster
mailing list.

***********************
Garbage Packet Received
***********************
If you're using StarCluster and encounter the following error you most likely
are not using a compatible StarCluster AMI::

    Traceback (most recent call last):
      File "/usr/lib/python2.6/site-packages/starcluster/threadpool.py", line 32, in run
        job.run()
      File "/usr/lib/python2.6/site-packages/starcluster/threadpool.py", line 59, in run
        r = self.method(*self.args, **self.kwargs)
      File "/usr/lib/python2.6/site-packages/starcluster/node.py", line 661, in set_hostname
        hostname_file = self.ssh.remote_file("/etc/hostname", "w")
      File "/usr/lib/python2.6/site-packages/starcluster/ssh.py", line 284, in remote_file
        rfile = self.sftp.open(file, mode)
      File "/usr/lib/python2.6/site-packages/starcluster/ssh.py", line 174, in sftp
        self._sftp = paramiko.SFTPClient.from_transport(self.transport)
      File "/usr/lib/python2.6/site-packages/paramiko/sftp_client.py", line 106, in from_transport
        return cls(chan)
      File "/usr/lib/python2.6/site-packages/paramiko/sftp_client.py", line 87, in __init__
        server_version = self._send_version()
      File "/usr/lib/python2.6/site-packages/paramiko/sftp.py", line 108, in _send_version
        t, data = self._read_packet()
      File "/usr/lib/python2.6/site-packages/paramiko/sftp.py", line 179, in _read_packet
        raise SFTPError('Garbage packet received')
    SFTPError: Garbage packet received

In this case you should update your ``NODE_IMAGE_ID`` setting in one of your
cluster templates in the config to point to a StarCluster AMI. You can get a
list of currently available StarCluster AMIs using the ``listpublic`` command::

    $ starcluster listpublic

You can also list available StarCluster AMIs in other regions::

    $ starcluster -r sa-east-1 listpublic
