import string
import random

from starcluster.clustersetup import DefaultClusterSetup
from starcluster.logger import log


class MPICH2Setup(DefaultClusterSetup):

    MPICH2_HOSTS = '/etc/mpich2.hosts'
    MPICH2_PROFILE = '/etc/profile.d/mpich2.sh'

    def _generate_secretword(self):
        log.info("Generating MPICH2 secretword")
        secretword = [x for x in (string.ascii_lowercase + string.digits)]
        random.shuffle(secretword)
        return ''.join(secretword)

    def _install_mpich(self, node):
        node.ssh.execute("apt-get --force-yes -y install mpich2")

    def _configure_hosts_file(self, node, aliases, secretword):
        mpich2_hosts = node.ssh.remote_file(self.MPICH2_HOSTS, 'w')
        mpich2_hosts.write('\n'.join(aliases))
        mpich2_hosts.close()
        mpich2_profile = node.ssh.remote_file(self.MPICH2_PROFILE, 'w')
        mpich2_profile.write("export HYDRA_HOST_FILE=%s" % self.MPICH2_HOSTS)

    def run(self, nodes, master, user, shell, volumes):
        secretword = self._generate_secretword()
        aliases = map(lambda x: x.alias, nodes)
        log.info("Installing mpich2 on all nodes")
        for node in nodes:
            self.pool.simple_job(self._install_mpich, (node), jobid=node.alias)
        self.pool.wait(len(nodes))
        log.info("Setting up MPICH2 hosts file on all nodes")
        for node in nodes:
            self.pool.simple_job(self._configure_hosts_file,
                                 (node, aliases, secretword),
                                 jobid=node.alias)
        self.pool.wait(len(nodes))
        log.info("MPICH2 is now ready to use")
        log.info("Use mpirun.mpich2 to run your MPI applications")
