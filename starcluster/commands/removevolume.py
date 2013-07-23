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

from completers import VolumeCompleter


class CmdRemoveVolume(VolumeCompleter):
    """
    removevolume [options] <volume_id>

    Delete one or more EBS volumes

    WARNING: This command will *PERMANENTLY* remove an EBS volume.
    Please use caution!

    Example:

        $ starcluster removevolume vol-999999
    """
    names = ['removevolume', 'rv']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, just "
                          "remove the volume")

    def execute(self, args):
        if not args:
            self.parser.error("no volumes specified. exiting...")
        for arg in args:
            volid = arg
            vol = self.ec2.get_volume(volid)
            if vol.status in ['attaching', 'in-use']:
                log.error("volume is currently in use. aborting...")
                return
            if vol.status == 'detaching':
                log.error("volume is currently detaching. "
                          "please wait a few moments and try again...")
                return
            if not self.opts.confirm:
                resp = raw_input("**PERMANENTLY** delete %s (y/n)? " % volid)
                if resp not in ['y', 'Y', 'yes']:
                    log.info("Aborting...")
                    return
            if vol.delete():
                log.info("Volume %s deleted successfully" % vol.id)
            else:
                log.error("Error deleting volume %s" % vol.id)
