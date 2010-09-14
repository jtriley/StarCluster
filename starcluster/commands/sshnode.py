#!/usr/bin/env python

import os
from starcluster import config
from starcluster import cluster
from starcluster import static
from starcluster import optcomplete
from starcluster.logger import log

from base import CmdBase

class CmdSshNode(CmdBase):
    """
    sshnode <cluster> <node>

    SSH to a cluster node

    Examples:

        $ starcluster sshnode mycluster master
        $ starcluster sshnode mycluster node001
        ...

    or same thing in shorthand:

        $ starcluster sshnode mycluster 0
        $ starcluster sshnode mycluster 1
        ...
    """
    names = ['sshnode', 'sn']

    @property
    def completer(self):
        if optcomplete:
            try:
                cfg = config.StarClusterConfig()
                cfg.load()
                ec2 = cfg.get_easy_ec2()
                clusters = cluster.get_cluster_security_groups(cfg)
                completion_list = [cluster.get_tag_from_sg(sg.name) for sg in clusters]
                max_num_nodes = 0
                for scluster in clusters:
                    num_instances = len(scluster.instances())
                    if num_instances > max_num_nodes:
                        max_num_nodes = num_instances
                completion_list.extend(['master'])
                completion_list.extend([str(i) for i in range(0,num_instances)])
                completion_list.extend(["node%03d" % i for i in range(1,num_instances)])
                return optcomplete.ListCompleter(completion_list)
            except Exception, e:
                print e
                log.error('something went wrong fix me: %s' % e)

    def addopts(self, parser):
        opt = parser.add_option("-u","--user", dest="USER", action="store",
                                type="string", default='root', 
                                help="login as USER (defaults to root)")

    def execute(self, args):
        if len(args) != 2:
            self.parser.error("please specify a <cluster> and <node> to connect to")
        scluster = args[0]
        ids = args[1:]
        for id in ids:
            cluster.ssh_to_cluster_node(scluster, id, self.cfg,
                                        user=self.opts.USER)
