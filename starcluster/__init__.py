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

import sys
from starcluster import static
sys.path.insert(0, static.STARCLUSTER_PLUGIN_DIR)

__version__ = static.VERSION
__author__ = "Justin Riley (justin.t.riley@gmail.com)"
__all__ = [
    "config",
    "static",
    "cluster",
    "clustersetup",
    "node",
    "sshutils",
    "plugins",
    "balancers",
    "managers",
    "validators",
    "image",
    "volume",
    "awsutils",
    "cli",
    "commands",
    "logger",
    "utils",
    "userdata",
    "webtools",
    "threadpool",
    "templates",
    "exception",
    "tests",
    "completion",
    "progressbar",
    "spinner",
]


def test():
    try:
        from nose import run
        run(argv=['sctest', '-s', '--exe', 'starcluster'], exit=False)
    except ImportError:
        print 'error importing nose'

test.__test__ = False
