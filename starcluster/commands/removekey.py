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

from base import CmdBase


class CmdRemoveKey(CmdBase):
    """
    removekey [options] <name>

    Remove a keypair from Amazon EC2
    """
    names = ['removekey', 'rk']

    def addopts(self, parser):
        parser.add_option("-c", "--confirm", dest="confirm",
                          action="store_true", default=False,
                          help="do not prompt for confirmation, just "
                          "remove the keypair")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please provide a key name")
        name = args[0]
        kp = self.ec2.get_keypair(name)
        if not self.opts.confirm:
            resp = raw_input("**PERMANENTLY** delete keypair %s (y/n)? " %
                             name)
            if resp not in ['y', 'Y', 'yes']:
                log.info("Aborting...")
                return
        log.info("Removing keypair: %s" % name)
        kp.delete()
