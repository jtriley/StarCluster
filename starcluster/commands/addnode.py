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

from starcluster import static
from completers import ClusterCompleter


class CmdAddNode(ClusterCompleter):
    """
    addnode [options] <cluster_tag>

    Add a node to a running cluster

    Examples:

        $ starcluster addnode mycluster

    This will launch a new node and add it to mycluster. The node's alias will
    be autogenerated based on the existing node aliases in the cluster.

    If you want to provide your own alias for the node use the -a option:

        $ starcluster addnode -a mynode mycluster

    This will add a new node called 'mynode' to mycluster.

    You can also add multiple nodes using the -n option:

        $ starcluster addnode -n 3 mycluster

    The above example will add three new nodes to mycluster with autogenerated
    aliases. If you'd rather provide your own aliases:

        $ starcluster addnode -a mynode1,mynode2,mynode3 mycluster

    This will add three new nodes to mycluster named mynode1, mynode2, and
    mynode3.

    If you've previously attempted to add a node and it failed due to a plugin
    error or other bug or if you used the 'removenode' command with the '-k'
    option and wish to re-add the node to the cluster without launching a new
    instance you can use the '-x' option:

        $ starcluster addnode -x -a mynode1 mycluster

    NOTE: The -x option requires the -a option

    This will add 'mynode1' to mycluster using the existing instance. If no
    instance exists with the alias specified by the '-a' option an error is
    reported. You can also do this for multiple nodes:

        $ starcluster addnode -x -a mynode1,mynode2,mynode3 mycluster
    """
    names = ['addnode', 'an']

    tag = None

    def addopts(self, parser):
        parser.add_option(
            "-a", "--alias", dest="alias", action="append", type="string",
            default=[], help="alias to give to the new node "
            "(e.g. node007, mynode, etc.)")
        parser.add_option(
            "-n", "--num-nodes", dest="num_nodes", action="store", type="int",
            default=1, help="number of new nodes to launch")
        parser.add_option(
            "-i", "--image-id", dest="image_id", action="store", type="string",
            default=None, help="image id for new node(s) "
            "(e.g. ami-12345678).")
        parser.add_option(
            "-I", "--instance-type", dest="instance_type",
            action="store", type="choice", default=None,
            choices=sorted(static.INSTANCE_TYPES.keys()),
            help="instance type to use when launching node")
        parser.add_option(
            "-z", "--availability-zone", dest="zone", action="store",
            type="string", default=None, help="availability zone for "
            "new node(s) (e.g. us-east-1)")
        parser.add_option(
            "-s", "--subnet", dest="subnet", action="store",
            type="string", default=None, help="subnet ID, use with -z (--availability-zone)")
        parser.add_option(
            "-b", "--bid", dest="spot_bid", action="store", type="float",
            default=None, help="spot bid for new node(s) (in $ per hour)")
        parser.add_option(
            "-x", "--no-create", dest="no_create", action="store_true",
            default=False, help="do not launch new EC2 instances when "
            "adding nodes (use existing instances instead)")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        tag = self.tag = args[0]
        aliases = []
        for alias in self.opts.alias:
            aliases.extend(alias.split(','))
        if ('master' in aliases) or ('%s-master' % tag in aliases):
            self.parser.error(
                "'master' and '%s-master' are reserved aliases" % tag)
        num_nodes = self.opts.num_nodes
        if num_nodes == 1 and aliases:
            num_nodes = len(aliases)
        if num_nodes > 1 and aliases and len(aliases) != num_nodes:
            self.parser.error("you must specify the same number of aliases "
                              "(-a) as nodes (-n)")
        dupe = self._get_duplicate(aliases)
        if dupe:
            self.parser.error("cannot have duplicate aliases (duplicate: %s)" %
                              dupe)
        if not self.opts.alias and self.opts.no_create:
            self.parser.error("you must specify one or more node aliases via "
                              "the -a option when using -x")
        self.cm.add_nodes(tag, num_nodes, aliases=aliases,
                          image_id=self.opts.image_id,
                          instance_type=self.opts.instance_type,
                          zone=self.opts.zone, spot_bid=self.opts.spot_bid,
                          subnet=self.opts.subnet, no_create=self.opts.no_create)
