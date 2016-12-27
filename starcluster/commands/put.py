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

import os

from starcluster import exception
from completers import ClusterCompleter


def list_csv(csv_string):
    """
    For parsing comma separated values in --multi e.g. --multi master,node001
    CommaSeparatedValues -> Nodename Generator

    Removes any empty strings from trailing commas
    >>> list_csv("master,node001,")
    ["master", "node001"]
    """
    return filter(bool, [name.strip() for name in csv_string.split(',')])


class CmdPut(ClusterCompleter):
    """
    put [options] <cluster_tag> [<local_file_or_dir> ...] <remote_destination>

    Copy files to a running cluster

    Examples:

        # Copy a file or dir to the master as root
        $ starcluster put mycluster /path/to/file/or/dir /path/on/remote/server

        # Copy one or more files or dirs to the master as root
        $ starcluster put mycluster /local/dir /local/file /remote/dir

        # Copy a file or dir to the master as normal user
        $ starcluster put mycluster --user myuser /local/path /remote/path

        # Copy a file or dir to a node (node001 in this example)
        $ starcluster put mycluster --node node001 /local/path /remote/path

        # Copy a file or dir to multiple nodes (master and node001 in this
        # example)
        $ starcluster put mycluster -m master,node001 /local/path /remote/path


    This will copy a file or directory to the remote server
    """
    names = ['put']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", default=None,
                          help="Transfer files as USER ")
        parser.add_option("-n", "--node", dest="node", default="master",
                          help="Transfer files to NODE (defaults to master)")
        parser.add_option("-m", "--multi", dest="multi", default=None,
                          help="Transfer files to multiple NODEs (defaults to "
                          + "master)")

    def put(self, node, rpath, lpaths):
        if self.opts.user:
            node.ssh.switch_user(self.opts.user)
        if len(lpaths) > 1 and not node.ssh.isdir(rpath):
            msg = "Remote path in %s does not exist: %s" % (node, rpath)
            raise exception.BaseException(msg)
        node.ssh.put(lpaths, rpath)

    def execute(self, args):
        if len(args) < 3:
            self.parser.error("please specify a cluster, local files or " +
                              "directories, and a remote destination path")
        ctag = args[0]
        rpath = args[-1]
        lpaths = args[1:-1]
        for lpath in lpaths:
            if not os.path.exists(lpath):
                raise exception.BaseException(
                    "Local file or directory does not exist: %s" % lpath)
        cl = self.cm.get_cluster(ctag, load_receipt=False)
        if self.opts.multi:
            nodes = [cl.get_node_by_alias(nodename) for nodename in
                     list_csv(self.opts.multi)]
        else:
            nodes = [cl.get_node_by_alias(self.opts.node)]
        for node in nodes:
            self.put(node, rpath, lpaths)
