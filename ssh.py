#!/usr/bin/env python
import os

"""Convenience methods for calling ssh/scp and creating ssh tunnels"""

def ssh(host, cmd = None, user='root', credential=None, silent=False, test=False):

    """ A simple ssh wrapper to execute a command on a remote host """

    if cmd == None:
        if not silent: 
            print 'WARNING: ssh.ssh: no command specified, logging in directly'
        cmd = ''

    d = {'cmd': cmd, 'user':user, 'host':host}

    d['switches'] = ''
    if credential:
        d['switches'] = '-i %s' % credential

    template = 'ssh %(switches)s -o "StrictHostKeyChecking no" %(user)s@%(host)s "%(cmd)s" '

    cmdline = template % d  

    if not silent:
        print "\n",cmdline,"\n\n"
    if not test:
        os.system(cmdline)

def scp(host, user='root', src=None, dest=None, recursive=False, credential=None, copyfrom = False, hostchecking=False, silent=False, test=False):

    """ A simple scp wrapper to copy files to and from a remote host """

    if not src or not dest:
        if not silent: 
            print 'ssh.scp: please specify a src/dest combo; returning...'
        return

    d = { 'user':user, 'src':src, 'dest':dest, 'host':host}

    d['hostchecking'] = ''
    if not hostchecking:
        d['hostchecking'] = '-o "StrictHostKeyChecking no"'

    d['switches'] = ''
    if credential:
        d['switches'] = '-i %s' % credential
    if recursive:
        d['switches'] = d['switches'] + ' -r'

    if copyfrom:
        template = 'scp %(switches)s %(hostchecking)s %(user)s@%(host)s:%(src)s %(dest)s' 
    else:
        template = 'scp %(switches)s %(hostchecking)s %(src)s %(user)s@%(host)s:%(dest)s' 

    cmdline = template % d  

    if not silent:
        print "\n",cmdline,"\n\n"
    if not test:
        os.system(cmdline)


class SSHTunnel(object):
    
    def __init__(self, target, dest_host = 'localhost', ssh_port = 22, forward_port = 5901, mode = 'open', reverse = False):

        self.config = {}
        config = self.config
        config['mode'] = mode
        config['target'] = target
        config['ssh_port'] = ssh_port
        config['forward_port'] = forward_port
        config['tunnel_option'] = '-L'
        config['dest_host'] = dest_host

        if reverse:
            config['tunnel_option'] = '-R'

    def remote(self, cmd = None):
        config = self.config
        if cmd is None or config['target'] is None:
            return
        self.config['cmd'] = cmd

        cmdline = "ssh -p %(ssh_port)s %(target)s %(cmd)s" % self.config
        os.system(cmdline)

    def open(self):
        print 'Tunneling port %s' % self.config['forward_port']

        # Initialize tunnel to run in the background.
        cmd = 'ssh %(tunnel_option)s %(forward_port)s:%(dest_host)s:%(forward_port)s -p %(ssh_port)s %(target)s -f -N' % self.config 
        os.system(cmd)
        

    def kill(self):

        cmd = 'ssh %(tunnel_option)s %(forward_port)s:%(dest_host)s:%(forward_port)s -p %(ssh_port)s %(target)s -f -N' % self.config 
        print 'Attempting to kill process: %s' % cmd

        put, get = os.popen4('pgrep -f -l ssh ')
        lines = get.readlines()
        for line in lines:
            if line.find(cmd) > 0:
                pid = int(line.split()[0])
                print 'tunnel found.  killing pid: %s ' % pid
                os.kill(pid,3)
