from starcluster import exception
from starcluster.logger import log

from completers import ClusterCompleter


class CmdTerminate(ClusterCompleter):
    """
    terminate [options] <cluster_tag> ...

    Terminate a running or stopped cluster

    Example:

        $ starcluster terminate mycluster

    This will terminate a currently running or stopped cluster tagged
    "mycluster".

    All nodes will be terminated, all spot requests (if any) will be
    cancelled, and the cluster's security group will be removed. If the
    cluster uses EBS-backed nodes then each node's root volume will be
    deleted.  If the cluster uses "cluster compute" instance types the
    cluster's placement group will also be removed.
    """
    names = ['terminate']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="Do not prompt for confirmation, "
                          "just terminate the cluster")

    def terminate_cluster(self, cluster_name):
        cl = self.cm.get_cluster(cluster_name, require_keys=False)
        if not self.opts.confirm:
            action = 'Terminate'
            if cl.is_ebs_cluster():
                action = 'Terminate EBS'
            resp = raw_input(
                "%s cluster %s (y/n)? " % (action, cluster_name))
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        cl.terminate_cluster()

    def terminate_manually(self, cluster_name):
        cl = self.cm.get_cluster(cluster_name, load_receipt=False)
        if not self.opts.confirm:
            resp = raw_input("Terminate cluster %s (y/n)? " % cluster_name)
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        insts = cl.cluster_group.instances()
        for inst in insts:
            log.info("Terminating %s" % inst.id)
            inst.terminate()
        cl.terminate_cluster()

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        for cluster_name in args:
            try:
                self.terminate_cluster(cluster_name)
            except exception.IncompatibleCluster:
                self.terminate_manually(cluster_name)
