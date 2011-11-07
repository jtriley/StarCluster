import re

from starcluster import clustersetup
from starcluster.templates import sge
from starcluster.logger import log


class SGEPlugin(clustersetup.DefaultClusterSetup):

    def _add_sge_submit_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -as %s' % node.alias, source_profile=True)

    def _add_sge_administrative_host(self, node):
        mssh = self._master.ssh
        mssh.execute('qconf -ah %s' % node.alias, source_profile=True)

    def _add_to_sge(self, node):
        # generate /etc/profile.d/sge.sh
        sge_profile = node.ssh.remote_file("/etc/profile.d/sge.sh")
        arch = node.ssh.execute("/opt/sge6/util/arch")[0]
        print >> sge_profile, sge.sgeprofile_template % {'arch': arch}
        sge_profile.close()
        node.ssh.execute('cd /opt/sge6 && TERM=rxvt ./inst_sge -x -noremote '
                         '-auto ./ec2_sge.conf')

    def _create_sge_pe(self, name="orte", nodes=None, queue="all.q"):
        """
        Create or update an SGE parallel environment

        name - name of parallel environment
        nodes - list of nodes to include in the parallel environment
                (default: all)
        queue - configure queue to use the new parallel environment
        """
        mssh = self._master.ssh
        pe_exists = mssh.get_status('qconf -sp %s' % name, source_profile=True)
        pe_exists = pe_exists == 0
        if not pe_exists:
            log.info("Creating SGE parallel environment '%s'" % name)
        else:
            log.info("Updating SGE parallel environment '%s'" % name)
        # iterate through each machine and count the number of processors
        nodes = nodes or self._nodes
        num_processors = sum(self.pool.map(lambda n: n.num_processors, nodes))
        penv = mssh.remote_file("/tmp/pe.txt")
        print >> penv, sge.sge_pe_template % (name, num_processors)
        penv.close()
        if not pe_exists:
            mssh.execute("qconf -Ap %s" % penv.name, source_profile=True)
        else:
            mssh.execute("qconf -Mp %s" % penv.name, source_profile=True)
        if queue:
            log.info("Adding parallel environment '%s' to queue '%s'" %
                     (name, queue))
            mssh.execute('qconf -mattr queue pe_list "%s" %s' % (name, queue),
                         source_profile=True)

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
        self._setup_nfs(self.nodes, export_paths=['/opt/sge6'])
        # generate /etc/profile.d/sge.sh for each node
        for node in self._nodes:
            conn = node.ssh
            conn.execute('pkill -9 sge', ignore_exit_status=True)
            conn.execute('rm /etc/init.d/sge*', ignore_exit_status=True)
            sge_profile = conn.remote_file("/etc/profile.d/sge.sh")
            arch = conn.execute("/opt/sge6/util/arch")[0]
            print >> sge_profile, sge.sgeprofile_template % {'arch': arch}
            sge_profile.close()
        # setup sge auto install file
        default_cell = '/opt/sge6/default'
        if master.ssh.isdir(default_cell):
            log.info("Removing previous SGE installation...")
            master.ssh.execute('rm -rf %s' % default_cell)
            master.ssh.execute('exportfs -fr')
        admin_list = ' '.join(map(lambda n: n.alias, self._nodes))
        exec_list = admin_list
        submit_list = admin_list
        ec2_sge_conf = master.ssh.remote_file("/opt/sge6/ec2_sge.conf")
        # TODO: add sge section to config values for some of the below
        conf = sge.sgeinstall_template % (admin_list, exec_list, submit_list)
        print >> ec2_sge_conf, conf
        ec2_sge_conf.close()
        # installs sge in /opt/sge6 and starts qmaster/schedd on master node
        log.info("Installing Sun Grid Engine...")
        master.ssh.execute(
            'cd /opt/sge6 && TERM=rxvt ./inst_sge -m -x -noremote '
            '-auto ./ec2_sge.conf', silent=True, only_printable=True)
        # set all.q shell to bash
        master.ssh.execute('qconf -mattr queue shell "/bin/bash" all.q',
                           source_profile=True)
        for node in self.nodes:
            self._add_sge_administrative_host(node)
            self._add_sge_submit_host(node)
            self.pool.simple_job(self._add_to_sge, (node,), jobid=node.alias)
        self.pool.wait(numtasks=len(self.nodes))
        self._create_sge_pe()

    def _remove_from_sge(self, node):
        master = self._master
        master.ssh.execute('qconf -shgrp @allhosts > /tmp/allhosts',
                           source_profile=True)
        hgrp_file = master.ssh.remote_file('/tmp/allhosts', 'r')
        contents = hgrp_file.read().splitlines()
        hgrp_file.close()
        c = []
        for line in contents:
            line = line.replace(node.alias, '')
            c.append(line)
        hgrp_file = master.ssh.remote_file('/tmp/allhosts_new', 'w')
        hgrp_file.writelines('\n'.join(c))
        hgrp_file.close()
        master.ssh.execute('qconf -Mhgrp /tmp/allhosts_new',
                           source_profile=True)
        master.ssh.execute('qconf -sq all.q > /tmp/allq', source_profile=True)
        allq_file = master.ssh.remote_file('/tmp/allq', 'r')
        contents = allq_file.read()
        allq_file.close()
        c = [l.strip() for l in contents.splitlines()]
        s = []
        allq = []
        for l in c:
            if l.startswith('slots') or l.startswith('['):
                s.append(l)
            else:
                allq.append(l)
        regex = re.compile(r"\[%s=\d+\],?" % node.alias)
        slots = []
        for line in s:
            line = line.replace('\\', '')
            slots.append(regex.sub('', line))
        allq.append(''.join(slots))
        f = master.ssh.remote_file('/tmp/allq_new', 'w')
        allq[-1] = allq[-1].strip()
        if allq[-1].endswith(','):
            allq[-1] = allq[-1][:-1]
        f.write('\n'.join(allq))
        f.close()
        master.ssh.execute('qconf -Mq /tmp/allq_new', source_profile=True)
        master.ssh.execute('qconf -dconf %s' % node.alias, source_profile=True)
        master.ssh.execute('qconf -de %s' % node.alias, source_profile=True)
        node.ssh.execute('pkill -9 sge_execd')
        nodes = filter(lambda n: n.alias != node.alias, self._nodes)
        self._create_sge_pe(nodes=nodes)

    def run(self, nodes, master, user, user_shell, volumes):
        try:
            self._nodes = nodes
            self._master = master
            self._user = user
            self._user_shell = user_shell
            self._volumes = volumes
            self._setup_sge()
        finally:
            self.pool.shutdown()

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Adding %s to SGE" % node.alias)
        self._setup_nfs(nodes=[node], export_paths=['/opt/sge6'],
                        start_server=False)
        self._add_sge_administrative_host(node)
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
