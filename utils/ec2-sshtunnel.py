#!/usr/bin/env python
import os
import re
import sys
import commands
import socket
from optparse import OptionParser

from starcluster import EC2
from starcluster.starclustercfg import *


class sshTunnel(object):
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


class HostFactory(object):
    def __init__(self):
        self.conn = EC2.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        self.ec2_hosts = []
        instance_response=self.conn.describe_instances()
        parsed_response=instance_response.parse()  

        if len(parsed_response) == 0:
            print 'No EC2 instances found. Start some with ec2-run-instances.' 
            return None

        for chunk in parsed_response:
            if chunk[0]=='INSTANCE':
                if chunk[-1]=='running' or chunk[-1]=='pending':
                    ip_address = socket.gethostbyname(chunk[3])
                    self.ec2_hosts.append([chunk[3], ip_address])

    def get_ec2_hosts(self):
        return self.ec2_hosts

def main():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option("-m","--mode", dest="mode", type="choice", choices = ['open','view', 'kill'], help="(open | kill)")
    parser.add_option("-u","--user", dest="user", help="user (passed as user@[ec2-host]. defaults to current user")
    parser.add_option("-n","--host", dest="host", type = "int", help="host number (in the order the host comes in ec2-describe-instances list")
    parser.add_option("-d","--dest_host", dest="dest_host", help="destination host (ie port:host:port")
    parser.add_option("-p","--ssh_port", dest="ssh_port", type = "int", help="port to use for ssh connection (defaults to 22)") 
    parser.add_option("-f","--forward-port", dest="forward", type="int", help="port to forward on local side") 
    parser.add_option("-r","--reverse-port", dest="reverse", type="int", help="port to forward on remote side") 

    (options,args) = parser.parse_args()
    if options.mode is not None:
        mode = options.mode
    else: 
        print 'must specify mode (-m) with either open or kill'
        print 'pass --help for details'
        sys.exit()
    
    user = options.user 

    if options.dest_host is not None:
        dest_host = options.dest_host 
    else: 
        dest_host = 'localhost'

    if options.ssh_port is not None:
        ssh_port = options.ssh_port 
    else:
        ssh_port = 22

    host_number = options.host
    forward = options.forward
    reverse = options.reverse
    tunnel_port = None

    if forward and reverse:
        print '>>> Error --forward and --reverse options are mutually exclusive...exiting'
        print '>>> pass --help for details'
        sys.exit()

    if reverse:
        reverse_connect = True
        tunnel_port = reverse
    elif forward:   
        reverse_connect = False
        tunnel_port = forward
    else: 
        print '>>> please specify a forward port (-f) or reverse port (-r)'
        print '>>> pass --help for details'
        sys.exit()
        
    host_factory = HostFactory()

    hosts = host_factory.get_ec2_hosts()

    if len(hosts) is 0:
        sys.exit()

    if host_number is None:
        for i in range(len(hosts)):
            print '[%s]  %s     %s' % (i, hosts[i][1], hosts[i][0])

        print '[q]  Quit this program'

        input = raw_input(">>> Please select a host number from above: ")

        if input in ['q','Q','quit','exit']:
            sys.exit()

        try:
            host_number = int(input)
        except:
            print '>>> Invalid selection...selecting host 0'
            host_number = 0 

        print ''

        if host_number not in range(len(hosts)):
           '>>> Invalid host_number.  Please enter one of: %s' % range(len(hosts))
           sys.exit() 

    target = '%s@%s' % (user, hosts[host_number][1])
    
    sshtunnel = sshTunnel(target, dest_host, ssh_port, tunnel_port ,mode, reverse_connect)

    try: 
        functions = {
            'open': sshtunnel.open,
            'connect': sshtunnel.open,
            'kill': sshtunnel.kill,
        } 

        func = functions[mode]
        func()
    except KeyError:
       parser.print_usage() 
       print '>>> Invalid/no mode specified \n'
       print 'Use --help to get a full list of options'


if __name__ == "__main__":
    main()
