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


class CmdCreateKey(CmdBase):
    """
    createkey [options] <name>

    Create a new Amazon EC2 keypair
    """
    names = ['createkey', 'ck']

    def addopts(self, parser):
        parser.add_option("-o", "--output-file", dest="output_file",
                          action="store", type="string", default=None,
                          help="Save the new keypair to a file")
        #parser.add_option("-a","--add-to-config", dest="add_to_config",
            #action="store_true", default=False,
            #help="add new keypair to StarCluster config")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please provide a key name")
        name = args[0]
        ofile = self.opts.output_file
        kp = self.ec2.create_keypair(name, output_file=ofile)
        log.info("Successfully created keypair: %s" % name)
        log.info("fingerprint: %s" % kp.fingerprint)
        log.info("contents: \n%s" % kp.material)
        if ofile:
            log.info("keypair written to %s" % ofile)
