from starcluster.clustersetup import DefaultClusterSetup
from starcluster.logger import log


class MPICH2Setup(DefaultClusterSetup):

    MPICH2_HOSTS = '/etc/mpich2.hosts'
    MPICH2_PROFILE = '/etc/profile.d/mpich2.sh'

    def _configure_hosts_file(self, node, aliases):
        mpich2_hosts = node.ssh.remote_file(self.MPICH2_HOSTS, 'w')
        mpich2_hosts.write('\n'.join(aliases))
        mpich2_hosts.close()
        mpich2_profile = node.ssh.remote_file(self.MPICH2_PROFILE, 'w')
        mpich2_profile.write("export HYDRA_HOST_FILE=%s" % self.MPICH2_HOSTS)

    def _update_alternatives(self, node):
        mpi_choices = node.ssh.execute("update-alternatives --list mpi")
        mpirun_choices = node.ssh.execute("update-alternatives --list mpirun")
        mpipath = None
        for choice in mpi_choices:
            if 'mpich2' in choice:
                mpipath = choice
                break
        mpirunpath = None
        for choice in mpirun_choices:
            if 'mpich2' in choice:
                mpirunpath = choice
                break
        node.ssh.execute("update-alternatives --set mpi %s" % mpipath)
        node.ssh.execute("update-alternatives --set mpirun %s" % mpirunpath)

    def run(self, nodes, master, user, shell, volumes):
        aliases = map(lambda x: x.alias, nodes)
        log.info("Setting up MPICH2 hosts file on all nodes")
        for node in nodes:
            self.pool.simple_job(self._configure_hosts_file,
                                 (node, aliases),
                                 jobid=node.alias)
        self.pool.wait(len(nodes))
        log.info("Setting MPICH2 as default MPI on all nodes")
        for node in nodes:
            self.pool.simple_job(self._update_alternatives, (node),
                                 jobid=node.alias)
        self.pool.wait(len(nodes))
        log.info("MPICH2 is now ready to use")
        log.info(
            "Use mpicc, mpif90, mpirun, etc. to compile and run your MPI apps")
