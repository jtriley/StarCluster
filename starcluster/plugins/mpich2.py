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

from starcluster import clustersetup
from starcluster.logger import log


class MPICH2Setup(clustersetup.DefaultClusterSetup):

    MPICH2_HOSTS = '/home/mpich2.hosts'
    MPICH2_PROFILE = '/etc/profile.d/mpich2.sh'

    def _configure_profile(self, node, aliases):
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
        log.info("Creating MPICH2 hosts file")
        aliases = [n.alias for n in nodes]
        mpich2_hosts = master.ssh.remote_file(self.MPICH2_HOSTS, 'w')
        mpich2_hosts.write('\n'.join(aliases) + '\n')
        mpich2_hosts.close()
        log.info("Configuring MPICH2 profile")
        for node in nodes:
            self.pool.simple_job(self._configure_profile,
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

    def on_add_node(self, new_node, nodes, master, user, user_shell, volumes):
        log.info("Adding %s to MPICH2 hosts file" % new_node.alias)
        mpich2_hosts = master.ssh.remote_file(self.MPICH2_HOSTS, 'a')
        mpich2_hosts.write(new_node.alias + '\n')
        mpich2_hosts.close()
        log.info("Setting MPICH2 as default MPI on %s" % new_node.alias)
        self._update_alternatives(new_node)

    def on_remove_node(self, remove_node, nodes, master, user, user_shell,
                       volumes):
        log.info("Removing %s from MPICH2 hosts file" % remove_node.alias)
        master.ssh.remove_lines_from_file(self.MPICH2_HOSTS, remove_node.alias)
