__version__ = "0.9999"
__author__ = "Justin Riley (justin.t.riley@gmail.com)"
__all__ = [
    "config", 
    "cli",
    "awsutils", 
    "balancers",
    "ssh", 
    "utils", 
    "static",
    "exception",
    "cluster", 
    "node",
    "clustersetup", 
    "image", 
    "volume", 
    "tests",
    "templates",
    "optcomplete",
]

import sys
from starcluster import static 
sys.path.insert(0,static.STARCLUSTER_PLUGIN_DIR)

def test():
    try:
        from nose.core import TestProgram
        p = TestProgram(argv=[__file__, "starcluster.tests", '-s'], exit=False)
    except ImportError:
        print 'error importing nose'
test.__test__ = False
