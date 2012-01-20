import os

from starcluster import exception
from completers import ClusterCompleter


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


    This will copy a file or directory to the remote server
    """
    names = ['put']

    def addopts(self, parser):
        parser.add_option("-u", "--user", dest="user", default=None,
                          help="Transfer files as USER ")
        parser.add_option("-n", "--node", dest="node", default="master",
                          help="Transfer files to NODE (defaults to master)")

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
        cl = self.cm.get_cluster(ctag)
        node = cl.get_node_by_alias(self.opts.node)
        if self.opts.user:
            node.ssh.switch_user(self.opts.user)
        if len(lpaths) > 1 and not node.ssh.isdir(rpath):
            raise exception.BaseException("Remote path does not exist: %s" %
                                          rpath)
        node.ssh.put(lpaths, rpath)
