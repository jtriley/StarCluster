from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log
 
class TaggerPlugin(ClusterSetup):
    def __init__(self, tags):
        self.tags = [t.strip() for t in tags.split(',')]
        self.tags = dict([t.split('=') for t in self.tags])
 
    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Tagging all nodes...")
        for tag in self.tags:
            val = self.tags.get(tag)
            log.info("Applying tag - %s: %s" % (tag, val))
            for node in nodes:
                node.add_tag(tag, val) 
