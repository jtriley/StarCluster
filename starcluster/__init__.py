__version__ = "0.91"
__author__ = "Justin Riley (justin.t.riley@gmail.com)"
__all__ = [
    "config", 
    "cli",
    "awsutils", 
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
