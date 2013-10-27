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

import optparse

from base import CmdBase


class CmdHelp(CmdBase):
    """
    help

    Show StarCluster usage
    """
    names = ['help']

    def execute(self, args):
        if args:
            cmdname = args[0]
            try:
                sc = self.subcmds_map[cmdname]
                lparser = optparse.OptionParser(sc.__doc__.strip())
                if hasattr(sc, 'addopts'):
                    sc.addopts(lparser)
                lparser.print_help()
            except KeyError:
                raise SystemExit("Error: invalid command '%s'" % cmdname)
        else:
            self.gparser.parse_args(['--help'])
