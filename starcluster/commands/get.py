# Copyright 2009-2013 Justin Riley
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

import glob

from starcluster import exception
from completers import ClusterCompleter


class CmdGet(ClusterCompleter):
    """
    get [options] <cluster_tag> [<remote_file_or_dir> ...] <local_destination>

    Copy one or more files from a running cluster to your local machine

    Examples:

        # Copy a file or dir from the master as root
        $ starcluster get mycluster /path/on/remote/server /local/file/or/dir

        # Copy a file and a dir from the master as root
        $ starcluster get mycluster /remote/file /remote/dir /local/dir

        # Copy a file or dir from the master as normal user
        $ starcluster get mycluster --user myuser /remote/path /local/path

        # Copy a file or dir from a node (node001 in this example)
        $ starcluster get mycluster --node node001 /remote/path /local/path

    """
    names = ['get']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", default=None,
                          help="Transfer files as USER ")
        parser.add_option("-n", "--node", dest="node", default="master",
                          help="Transfer files from NODE (defaults to master)")

    def execute(self, args):
        if len(args) < 3:
            self.parser.error("please specify a cluster, remote file or " +
                              "directory, and a local destination path")
        ctag = args[0]
        lpath = args[-1]
        rpaths = args[1:-1]
        cl = self.cm.get_cluster(ctag, load_receipt=False)
        node = cl.get_node_by_alias(self.opts.node)
        if self.opts.user:
            node.ssh.switch_user(self.opts.user)
        for rpath in rpaths:
            if not glob.has_magic(rpath) and not node.ssh.path_exists(rpath):
                raise exception.BaseException(
                    "Remote file or directory does not exist: %s" % rpath)
        node.ssh.get(rpaths, lpath)
