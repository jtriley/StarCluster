
import traceback
import re
from starcluster import clustersetup
from starcluster.templates import sge
from starcluster.logger import log

class DatacraticDevPlugin(clustersetup.DefaultClusterSetup):

    def run(self, nodes, master, user, user_shell, volumes):
        master.ec2.get_instance(master.id).add_tag("bluekai-prod", "")

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        node.ec2.get_instance(node.id).add_tag("bluekai-prod", "")
