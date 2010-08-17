from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log

class IPCluster(ClusterSetup):
    """
    Starts an IPCluster on StarCluster
    """

    cluster_file = '/etc/clusterfile.py'
    log_file = '/var/log/ipcluster.log'

    def run(self, nodes, master, user, user_shell, volumes):
        send_furl = True
        engines = {}
        for node in nodes:
            engines[node.private_dns_name] = node.num_processors
        f = master.ssh.remote_file(self.cluster_file,'w')
        f.writelines('send_furl = True\n')
        f.writelines('engines = %s\n' % engines)
        f.close()
        log.info("Starting ipcluster...")
        master.ssh.execute(
            "su - %s -c 'screen -d -m ipcluster ssh --clusterfile %s'" %
                                 (user, self.cluster_file))
