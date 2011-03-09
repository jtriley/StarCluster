import sys
from starcluster import static
sys.path.insert(0, static.STARCLUSTER_PLUGIN_DIR)

__version__ = "0.9999"
__author__ = "Justin Riley (justin.t.riley@gmail.com)"
__all__ = [
    "config",
    "cluster",
    "clustersetup",
    "node",
    "ssh",
    "plugins",
    "balancers",
    "managers",
    "image",
    "volume",
    "awsutils",
    "cli",
    "commands",
    "logger",
    "utils",
    "iptools",
    "static",
    "templates",
    "exception",
    "tests",
    "optcomplete",
    "progressbar",
    "spinner",
]


def test():
    try:
        from nose.core import TestProgram
        TestProgram(argv=[__file__, "starcluster.tests", '-s'], exit=False)
    except ImportError:
        print 'error importing nose'

test.__test__ = False
