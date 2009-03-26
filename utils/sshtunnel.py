#!/usr/bin/env python
import os,sys
from optparse import OptionParser
from starcluster.ssh import SSHTunnel

def main(args):
    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option("-m","--mode", dest="mode", type="choice", choices = ['open','view', 'kill'], help="(open | kill)")
    parser.add_option("-u","--user", dest="user", help="user (passed as user@host. defaults to current user")
    parser.add_option("-n","--host", dest="host", type = "int", help="host to ssh to")
    parser.add_option("-d","--dest_host", dest="dest_host", help="destination host (ie port:host:port")
    parser.add_option("-p","--ssh_port", dest="ssh_port", type = "int", help="port to use for ssh connection (defaults to 22)") 
    parser.add_option("-f","--forward-port", dest="forward", type="int", help="port to forward on local side") 
    parser.add_option("-r","--reverse-port", dest="reverse", type="int", help="port to forward on remote side") 

    (options,args) = parser.parse_args(args)

    if options.mode is not None:
        mode = options.mode
    else: 
        print 'must specify mode (-m) with either open or kill'
        print 'pass --help for details'
        sys.exit()

    if options.user is not None:    
        user = options.user 
    else:
        print 'no user specified, logging in as current user...'
        user = os.getlogin()

    if options.dest_host is not None:
        dest_host = options.dest_host 
    else: 
        dest_host = 'localhost'

    if options.ssh_port is not None:
        ssh_port = options.ssh_port 
    else:
        ssh_port = 22

    host = options.host
    forward = options.forward
    reverse = options.reverse
    tunnel_port = None

    if forward and reverse:
        print 'Error --forward and --reverse options are mutually exclusive...exiting'
        print 'pass --help for details'
        sys.exit()

    if reverse:
        reverse_connect = True
        tunnel_port = reverse
    elif forward:   
        reverse_connect = False
        tunnel_port = forward
    else: 
        print 'please specify a forward port (-f) or reverse port (-r)'
        print 'pass --help for details'
        sys.exit()

    if host is None:
        sys.exit()

    target = '%s@%s' % (user, host)
    
    sshtunnel = SSHTunnel(target, dest_host, ssh_port, tunnel_port ,mode, reverse_connect)

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
       print 'Invalid/no mode specified \n'
       print 'Use --help to get a full list of options'

if __name__ == "__main__":
    main(sys.argv)
