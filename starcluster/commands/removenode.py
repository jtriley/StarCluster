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
import warnings

from starcluster.logger import log
from starcluster.commands.completers import ClusterCompleter


class CmdRemoveNode(ClusterCompleter):
    """
    removenode [options] <cluster_tag>

    Terminate one or more nodes in the cluster

    Examples:

        $ starcluster removenode mycluster

    This will automatically fetch a single worker node, detach it from the
    cluster, and then terminate it. If you'd rather be specific about which
    node(s) to remove then use the -a option:

        $ starcluster removenode mycluster -a node003

    You can also specify multiple nodes to remove and terminate one after
    another, e.g.:

        $ starcluster removenode mycluster -n 3

    or

        $ starcluster removenode mycluster -a node001,node002,node003

    If you'd rather not terminate the node(s) after detaching from the cluster,
    use the -k option:

        $ starcluster removenode -k mycluster -a node001,node002,node003

    This will detach the nodes from the cluster but leave the instances
    running. These nodes can then later be reattached to the cluster using:

        $ starcluster addnode mycluster -x -a node001,node002,node003

    This can be useful, for example, when testing on_add_node and
    on_remove_node methods in a StarCluster plugin.
    """
    names = ['removenode', 'rn']

    tag = None

    def addopts(self, parser):
        parser.add_option("-f", "--force", dest="force", action="store_true",
                          default=False,  help="Terminate node regardless "
                          "of errors if possible ")
        parser.add_option("-k", "--keep-instance", dest="terminate",
                          action="store_false", default=True,
                          help="do not terminate nodes "
                          "after detaching them from the cluster")
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="Do not prompt for confirmation, "
                          "just remove the node(s)")
        parser.add_option("-n", "--num-nodes", dest="num_nodes",
                          action="store", type="int", default=1,
                          help="number of nodes to remove")
        parser.add_option("-a", "--aliases", dest="aliases", action="append",
                          type="string", default=[],
                          help="list of nodes to remove (e.g. "
                          "node001,node002,node003)")

    def execute(self, args):
        if not len(args) >= 1:
            self.parser.error("please specify a cluster <cluster_tag>")
        if len(args) >= 2:
            warnings.warn(
                "Passing node names as arguments is deprecated. Please "
                "start using the -a option. Pass --help for more details",
                DeprecationWarning)
        tag = self.tag = args[0]
        aliases = []
        for alias in self.opts.aliases:
            aliases.extend(alias.split(','))
        old_form_aliases = args[1:]
        if old_form_aliases:
            if aliases:
                self.parser.error(
                    "you must either use a list of nodes as arguments OR "
                    "use the -a option - not both")
            else:
                aliases = old_form_aliases
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
        if not self.opts.confirm:
            resp = raw_input("Remove %s from %s (y/n)? " %
                             (', '.join(aliases) or '%s nodes' % num_nodes,
                              tag))
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        self.cm.remove_nodes(tag, aliases=aliases, num_nodes=num_nodes,
                             terminate=self.opts.terminate,
                             force=self.opts.force)
