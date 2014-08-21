# Copyright 2009-2014 Justin Riley
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


def test_nose():
    try:
        from nose import run
        run(argv=['sctest', '-s', '--exe', 'starcluster'], exit=False)
    except ImportError:
        print 'error importing nose'


def test_pytest():
    try:
        import pytest
        import os
        pytest.main('-xvs %s' % os.path.dirname(__file__))
    except ImportError:
        print 'error importing pytest'


def test(use_nose=False):
    if use_nose:
        test_nose()
    else:
        test_pytest()


test_nose.__test__ = False
test_pytest.__test__ = False
test.__test__ = False
