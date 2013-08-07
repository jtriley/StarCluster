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
        parser.add_option("-f", "--force", dest="force", action="store_true",
                          default=False,  help="Terminate cluster regardless "
                          "of errors if possible ")

    def _terminate_cluster(self, cl):
        if not self.opts.confirm:
            action = 'Terminate'
            if cl.is_ebs_cluster():
                action = 'Terminate EBS'
            resp = raw_input(
                "%s cluster %s (y/n)? " % (action, cl.cluster_tag))
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        cl.terminate_cluster()

    def _terminate_manually(self, cl):
        if not self.opts.confirm:
            resp = raw_input("Terminate cluster %s (y/n)? " % cl.cluster_tag)
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        insts = cl.cluster_group.instances()
        for inst in insts:
            log.info("Terminating %s" % inst.id)
            inst.terminate()
        cl.terminate_cluster(force=True)

    def terminate(self, cluster_name, force=False):
        if force:
            log.warn("Ignoring cluster settings due to --force option")
        try:
            cl = self.cm.get_cluster(cluster_name, load_receipt=not force,
                                     require_keys=not force)
            if force:
                self._terminate_manually(cl)
            else:
                self._terminate_cluster(cl)
        except exception.ClusterDoesNotExist:
            raise
        except Exception:
            log.error("Failed to terminate cluster!", exc_info=True)
            if not force:
                log.error("Use -f to forcefully terminate the cluster")
            raise

    def execute(self, args):
        if not args:
            self.parser.error("please specify a cluster")
        for cluster_name in args:
            try:
                self.terminate(cluster_name, force=self.opts.force)
            except EOFError:
                print 'Interrupted, exiting...'
                return
