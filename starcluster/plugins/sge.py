# Copyright 2009-2014 Justin Riley
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
import posixpath

from starcluster import clustersetup
from starcluster.templates import sge
from starcluster.logger import log


class SGEPlugin(clustersetup.DefaultClusterSetup):
    SGE_ROOT = "/opt/sge6"
    SGE_FRESH = "/opt/sge6-fresh"
    SGE_PROFILE = "/etc/profile.d/sge.sh"
    SGE_INST = "inst_sge_sc"
    SGE_CONF = "ec2_sge.conf"

    def __init__(self, master_is_exec_host=True, slots_per_host=None,
                 **kwargs):
        self.master_is_exec_host = str(master_is_exec_host).lower() == "true"
        self.slots_per_host = None
        if slots_per_host is not None:
            self.slots_per_host = int(slots_per_host)
        super(SGEPlugin, self).__init__(**kwargs)

    def _add_sge_submit_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -as %s' % node.alias)

    def _add_sge_admin_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -ah %s' % node.alias)

    def _setup_sge_profile(self, node):
        sge_profile = node.ssh.remote_file(self.SGE_PROFILE, "w")
        arch = node.ssh.execute(self._sge_path("util/arch"))[0]
        sge_profile.write(sge.sgeprofile_template % dict(arch=arch))
        sge_profile.close()

    def _add_to_sge(self, node):
        node.ssh.execute('pkill -9 sge', ignore_exit_status=True)
        node.ssh.execute('rm /etc/init.d/sge*', ignore_exit_status=True)
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
        if not nodes:
            nodes = self._nodes if self.master_is_exec_host else self.nodes
        if self.slots_per_host is None:
            pe_slots = sum(self.pool.map(lambda n: n.num_processors, nodes,
                                         jobid_fn=lambda n: n.alias))
        else:
            pe_slots = self.slots_per_host * len(nodes)
        if not pe_exists:
            penv = mssh.remote_file("/tmp/pe.txt", "w")
            penv.write(sge.sge_pe_template % (name, pe_slots))
            penv.close()
            mssh.execute("qconf -Ap %s" % penv.name)
        else:
            mssh.execute("qconf -mattr pe slots %s %s" % (pe_slots, name))
        if queue:
            log.info("Adding parallel environment '%s' to queue '%s'" %
                     (name, queue))
            mssh.execute('qconf -mattr queue pe_list "%s" %s' % (name, queue))

    def _inst_sge(self, node, exec_host=True):
        self._setup_sge_profile(node)
        inst_sge = 'cd %s && TERM=rxvt ./%s ' % (self.SGE_ROOT, self.SGE_INST)
        if node.is_master():
            inst_sge += '-m '
        if exec_host:
            inst_sge += '-x '
        inst_sge += '-noremote -auto ./%s' % self.SGE_CONF
        node.ssh.execute(inst_sge, silent=True, only_printable=True)
        if exec_host:
            num_slots = self.slots_per_host
            if num_slots is None:
                num_slots = node.num_processors
            node.ssh.execute("qconf -aattr hostgroup hostlist %s @allhosts" %
                             node.alias)
            node.ssh.execute('qconf -aattr queue slots "[%s=%d]" all.q' %
                             (node.alias, num_slots))

    def _sge_path(self, path):
        return posixpath.join(self.SGE_ROOT, path)

    def _disable_add_queue(self):
        """
        Disables the install script from automatically adding the exec host to
        the queue with slots=num_cpus so that this plugin can customize the
        number of slots *before* the node is available to accept jobs.
        """
        master = self._master
        master.ssh.execute("cd %s && sed 's/AddQueue/#AddQueue/g' inst_sge > "
                           "%s" % (self.SGE_ROOT, self.SGE_INST))
        master.ssh.chmod(0755, self._sge_path(self.SGE_INST))

    def _setup_sge(self):
        """
        Install Sun Grid Engine with a default parallel environment on
        StarCluster
        """
        master = self._master
        if not master.ssh.isdir(self.SGE_ROOT):
            # copy fresh sge installation files to SGE_ROOT
            master.ssh.execute('cp -r %s %s' % (self.SGE_FRESH, self.SGE_ROOT))
            master.ssh.execute('chown -R %(user)s:%(user)s %(sge_root)s' %
                               {'user': self._user, 'sge_root': self.SGE_ROOT})
        self._disable_add_queue()
        self._setup_nfs(self.nodes, export_paths=[self.SGE_ROOT],
                        start_server=False)
        # setup sge auto install file
        default_cell = self._sge_path('default')
        if master.ssh.isdir(default_cell):
            log.info("Removing previous SGE installation...")
            master.ssh.execute('rm -rf %s' % default_cell)
            master.ssh.execute('exportfs -fr')
        admin_hosts = ' '.join(map(lambda n: n.alias, self._nodes))
        submit_hosts = admin_hosts
        exec_hosts = admin_hosts
        sge_conf = master.ssh.remote_file(self._sge_path(self.SGE_CONF), "w")
        conf = sge.sgeinstall_template % dict(admin_hosts=admin_hosts,
                                              submit_hosts=submit_hosts,
                                              exec_hosts=exec_hosts)
        sge_conf.write(conf)
        sge_conf.close()
        log.info("Installing Sun Grid Engine...")
        self._inst_sge(master, exec_host=self.master_is_exec_host)
        # set all.q shell to bash
        master.ssh.execute('qconf -mattr queue shell "/bin/bash" all.q')
        for node in self.nodes:
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
        if not master.ssh.isdir(self.SGE_FRESH):
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
        self._setup_nfs(nodes=[node], export_paths=[self.SGE_ROOT],
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
