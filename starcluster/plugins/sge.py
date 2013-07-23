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
from starcluster.templates import sge
from starcluster.logger import log


class SGEPlugin(clustersetup.DefaultClusterSetup):

    def __init__(self, master_is_exec_host=True, **kwargs):
        self.master_is_exec_host = str(master_is_exec_host).lower() == "true"
        super(SGEPlugin, self).__init__(**kwargs)

    def _add_sge_submit_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -as %s' % node.alias)

    def _add_sge_admin_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -ah %s' % node.alias)

    def _setup_sge_profile(self, node):
        sge_profile = node.ssh.remote_file("/etc/profile.d/sge.sh", "w")
        arch = node.ssh.execute("/opt/sge6/util/arch")[0]
        sge_profile.write(sge.sgeprofile_template % dict(arch=arch))
        sge_profile.close()

    def _add_to_sge(self, node):
        node.ssh.execute('pkill -9 sge', ignore_exit_status=True)
        node.ssh.execute('rm /etc/init.d/sge*', ignore_exit_status=True)
        self._setup_sge_profile(node)
        self._inst_sge(node, exec_host=True)

    def _create_sge_pe(self, name="orte", nodes=None, queue="all.q"):
        """
        Create or update an SGE parallel environment

        name - name of parallel environment
        nodes - list of nodes to include in the parallel environment
                (default: all)
        queue - configure queue to use the new parallel environment
        """
        mssh = self._master.ssh
        pe_exists = mssh.get_status('qconf -sp %s' % name) == 0
        verb = 'Updating' if pe_exists else 'Creating'
        log.info("%s SGE parallel environment '%s'" % (verb, name))
        # iterate through each machine and count the number of processors
        nodes = nodes or self._nodes
        num_processors = sum(self.pool.map(lambda n: n.num_processors, nodes,
                                           jobid_fn=lambda n: n.alias))
        if not pe_exists:
            penv = mssh.remote_file("/tmp/pe.txt", "w")
            penv.write(sge.sge_pe_template % (name, num_processors))
            penv.close()
            mssh.execute("qconf -Ap %s" % penv.name)
        else:
            mssh.execute("qconf -mattr pe slots %s %s" %
                         (num_processors, name))
        if queue:
            log.info("Adding parallel environment '%s' to queue '%s'" %
                     (name, queue))
            mssh.execute('qconf -mattr queue pe_list "%s" %s' % (name, queue))

    def _inst_sge(self, node, exec_host=True):
        inst_sge = 'cd /opt/sge6 && TERM=rxvt ./inst_sge '
        if node.is_master():
            inst_sge += '-m '
        if exec_host:
            inst_sge += '-x '
        inst_sge += '-noremote -auto ./ec2_sge.conf'
        node.ssh.execute(inst_sge, silent=True, only_printable=True)

    def _setup_sge(self):
        """
        Install Sun Grid Engine with a default parallel
        environment on StarCluster
        """
        master = self._master
        if not master.ssh.isdir('/opt/sge6'):
            # copy fresh sge installation files to /opt/sge6
            master.ssh.execute('cp -r /opt/sge6-fresh /opt/sge6')
            master.ssh.execute('chown -R %(user)s:%(user)s /opt/sge6' %
                               {'user': self._user})
        self._setup_nfs(self.nodes, export_paths=['/opt/sge6'],
                        start_server=False)
        # setup sge auto install file
        default_cell = '/opt/sge6/default'
        if master.ssh.isdir(default_cell):
            log.info("Removing previous SGE installation...")
            master.ssh.execute('rm -rf %s' % default_cell)
            master.ssh.execute('exportfs -fr')
        admin_hosts = ' '.join(map(lambda n: n.alias, self._nodes))
        submit_hosts = admin_hosts
        exec_hosts = admin_hosts
        ec2_sge_conf = master.ssh.remote_file("/opt/sge6/ec2_sge.conf", "w")
        conf = sge.sgeinstall_template % dict(admin_hosts=admin_hosts,
                                              submit_hosts=submit_hosts,
                                              exec_hosts=exec_hosts)
        ec2_sge_conf.write(conf)
        ec2_sge_conf.close()
        log.info("Installing Sun Grid Engine...")
        self._inst_sge(master, exec_host=self.master_is_exec_host)
        self._setup_sge_profile(master)
        # set all.q shell to bash
        master.ssh.execute('qconf -mattr queue shell "/bin/bash" all.q')
        for node in self.nodes:
            self._add_sge_admin_host(node)
            self._add_sge_submit_host(node)
            self.pool.simple_job(self._add_to_sge, (node,), jobid=node.alias)
        self.pool.wait(numtasks=len(self.nodes))
        self._create_sge_pe()

    def _remove_from_sge(self, node):
        master = self._master
        master.ssh.execute('qconf -dattr hostgroup hostlist %s @allhosts' %
                           node.alias)
        master.ssh.execute('qconf -purge queue slots all.q@%s' % node.alias)
        master.ssh.execute('qconf -dconf %s' % node.alias)
        master.ssh.execute('qconf -de %s' % node.alias)
        node.ssh.execute('pkill -9 sge_execd')
        nodes = filter(lambda n: n.alias != node.alias, self._nodes)
        self._create_sge_pe(nodes=nodes)

    def run(self, nodes, master, user, user_shell, volumes):
        if not master.ssh.isdir("/opt/sge6-fresh"):
            log.error("SGE is not installed on this AMI, skipping...")
            return
        log.info("Configuring SGE...")
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        self._setup_sge()

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Adding %s to SGE" % node.alias)
        self._setup_nfs(nodes=[node], export_paths=['/opt/sge6'],
                        start_server=False)
        self._add_sge_admin_host(node)
        self._add_sge_submit_host(node)
        self._add_to_sge(node)
        self._create_sge_pe()

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Removing %s from SGE" % node.alias)
        self._remove_from_sge(node)
        self._remove_nfs_exports(node)
