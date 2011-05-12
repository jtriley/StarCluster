#!/usr/bin/env python

from completers import ClusterCompleter

##changes
#   added image_id, instance_type, availability zone, and spot_bid options

class CmdAddNode(ClusterCompleter):
    """
    addnode [options] <cluster_tag>

    Add a node to a running cluster

    Example:

        $ starcluster addnode mynewcluster

    This will add a new node to mynewcluster. To give the node an alias:

        $ starcluster addnode -a mynode mynewcluster
    """
    names = ['addnode', 'an']

    tag = None

    def addopts(self, parser):
        parser.add_option("-a", "--alias", dest="alias",
                          action="store", type="string", default=None,
                          help=("alias to give to the new node " + \
                                "(e.g. node007, mynode, etc)"))
        parser.add_option("-i", "--image-id", dest="image_id",
                          action="store", type="string", default=None,
                          help=("image id for new node " + \
                                "(e.g. ami-12345678)"))                                
        parser.add_option("-I", "--instance-type", dest="instance_type",
                          action="store", type="string", default=None,
                          help=("instance type for new node " + \
                                "(e.g. m1.large, cg1.4xlarge, etc)"))  
        parser.add_option("-z", "--availability-zone", dest="zone",
                          action="store", type="string", default=None,
                          help=("availability zone for new node " + \
                                "(e.g. us-east-1)"))                                  
        parser.add_option("-b", "--bid", dest="spot_bid",
                          action="store", type="float", default=None,
                          help=("spot bid for new node, in dollars per hour" + \
                                "(i.e. .24 means 24 cents/hr)"))  

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = self.tag = args[0]
        ##i think this is wrong ... isn't this step taken care of in Cluster.add_node?  
        #aliases = None     
        #if self.opts.alias:
        #    aliases = [self.opts.alias]    
        self.cm.add_node(tag, alias = self.opts.alias,
        					  image_id = self.opts.image_id,
        					  instance_type = self.opts.instance_type,
        					  zone = self.opts.zone,
        					  spot_bid = self.opts.spot_bid)


