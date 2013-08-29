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

from starcluster.logger import log

from completers import SnapshotCompleter

class CmdRemoveSnapshot(SnapshotCompleter):
    """
    removesnapshot [options] <snapshot_id>

    Delete one or more EBS snapshots

    WARNING: This command will *PERMANENTLY* remove an EBS snapshot.
    Please use caution!

    Example:

        $ starcluster removesnapshot snap-999999
    """
    names = ['removesnapshot', 'rs']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, just "
                          "remove the snapshot")

    def execute(self, args):
        if not args:
            self.parser.error("no snapshots specified. exiting...")
        for arg in args:
            snapid = arg
            snap = self.ec2.get_snapshot(snapid)
            if snap.status in ['attaching', 'in-use']:
                log.error("snapshot is currently in use. aborting...")
                return
            if snap.status == 'detaching':
                log.error("snapshot is currently detaching. "
                          "please wait a few moments and try again...")
                return
            if not self.opts.confirm:
                resp = raw_input("**PERMANENTLY** delete %s (y/n)? " % snapid)
                if resp not in ['y', 'Y', 'yes']:
                    log.info("Aborting...")
                    return
            if snap.delete():
                log.info("Snapshot %s deleted successfully" % snap.id)
            else:
                log.error("Error deleting snapshot %s" % snap.id)
