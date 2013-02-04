from starcluster import clustersetup
from starcluster.templates import sge
from starcluster.logger import log
import xml.etree.ElementTree as ET
import time


class DeadNode():
    alias = None

    def __init__(self, alias):
        self.alias = alias


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
        pe_exists = mssh.get_status('qconf -sp %s' % name)
        pe_exists = pe_exists == 0
        verb = 'Updating'
        if not pe_exists:
            verb = 'Creating'
        log.info("%s SGE parallel environment '%s'" % (verb, name))
        # iterate through each machine and count the number of processors
        nodes = nodes or self._nodes
        #TODO: Fails if some machines go away while updating
        num_processors = sum(self.pool.map(lambda n: n.num_processors, nodes))
        penv = mssh.remote_file("/tmp/pe.txt", "w")
        penv.write(sge.sge_pe_template % (name, num_processors))
        penv.close()
        if not pe_exists:
            mssh.execute("qconf -Ap %s" % penv.name)
        else:
            mssh.execute("qconf -Mp %s" % penv.name)
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

    def _remove_from_sge(self, node, only_clean_master=False):
        master = self._master
        master.ssh.execute('qconf -dattr hostgroup hostlist %s @allhosts' %
                           node.alias)
        master.ssh.execute('qconf -purge queue slots all.q@%s' % node.alias)
        master.ssh.execute('qconf -dconf %s' % node.alias)
        master.ssh.execute('qconf -de %s' % node.alias)
        if not only_clean_master:
            node.ssh.execute('pkill -9 sge_execd', ignore_exit_status=True)
        nodes = filter(lambda n: n.alias != node.alias, self._nodes)
        self._create_sge_pe(nodes=nodes)

    def get_nodes_to_recover(self, nodes):
        """
        Active nodes that are not in OGS.
        """
        if len(nodes) == 1:
            return []

        master = nodes[0]
        qhosts = master.ssh.execute("qhost", source_profile=True)
        qhosts = qhosts[3:]
        missing = []
        aliases = []
        for line in qhosts:
            aliases.append(line[0:line.find(" ")])
        for node in nodes:
            if node.alias not in aliases:
                missing.append(node)

        return missing

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

    """
    Run qhost to find nodes that are present in OGS but not in the cluster in
    order to remove them.
    """
    def clean_cluster(self, nodes, master, user, user_shell, volumes):
        self._master = master
        self._nodes = nodes
        qhosts = self._master.ssh.execute("qhost", source_profile=True)
        if len(qhosts) <= 3:
            log.info("Nothing to clean")

        qhosts = qhosts[3:]
        aliveNodes = [node.alias for node in nodes]

        cleaned = []
        #find dead hosts
        for qhost in qhosts:
            nodeAlias = qhost[0:qhost.find(" ")]
            if nodeAlias not in aliveNodes:
                cleaned.append(nodeAlias)

        #find jobs running in dead hosts
        qstatsXml = self._master.ssh.execute("qstat -xml", source_profile=True)
        qstatsXml[1:]  # remove first line
        qstatsET = ET.fromstringlist(qstatsXml)
        toDelete = []
        toRepair = []
        cleanedQueue = []  # not a lambda function to allow pickling
        for c in cleaned:
            cleanedQueue.append("all.q@" + c)
        for jobList in qstatsET.find("queue_info").findall("job_list"):
            if jobList.find("queue_name").text in cleanedQueue:
                jobNumber = jobList.find("JB_job_number").text
                toDelete.append(jobNumber)
        for jobList in qstatsET.find("job_info").findall("job_list"):
            if jobList.find("state").text == "Eqw":
                jobNumber = jobList.find("JB_job_number").text
                toRepair.append(jobNumber)
        #delete the jobs
        if toDelete:
            log.info("Stopping jobs: " + str(toDelete))
            self._master.ssh.execute("qdel -f " + " ".join(toDelete))
            time.sleep(3)  # otherwise might provoke LOST QRSH if on last job
        if toRepair:
            log.error("Reseting jobs: " + str(toRepair))
            self._master.ssh.execute("qmod -cj " + " ".join(toRepair),
                                     ignore_exit_status=True)

        #DEBUGIN stuck qrsh issue (BLUK-63)
        ps_wc = int(self._master.ssh.execute("ps -ef | grep qrsh | wc -l")[0])
        qstat_wc = int(self._master.ssh.execute("qstat | wc -l")[0])
        if qstat_wc == 0 and ps_wc > 2:
            log.error("LOST QRSH??")
            from datetime import datetime
            now = str(datetime.utcnow()).replace(" ", "_")
            log.error("Dumping qstats")
            self._master.ssh.execute("qstat -ext > qstats_" + now)
            log.error("Dumping qacct")
            self._master.ssh.execute("qacct -j > qacct_" + now)
            log.error("pkill -9 qrsh")
            self._master.ssh.execute("pkill -9 qrsh", ignore_exit_status=True)
        #----------------------------------

        #delete the host config
        for c in cleaned:
            log.info("Cleaning node " + c)
            self._remove_from_sge(DeadNode(c), only_clean_master=True)

        #fix to allow pickling
        self._master = None
        self._nodes = None

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

        #fix to allow pickling
        self._nodes = None
        self._master = None
        self._user = None
        self._user_shell = None
        self._volumes = None
        if self._pool:
            self._pool.shutdown()
            self._pool = None

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Removing %s from SGE" % node.alias)
        self._remove_from_sge(node)
        self._remove_nfs_exports(node)

        #fix to allow pickling
        self._nodes = None
        self._master = None
        self._user = None
        self._user_shell = None
        self._volumes = None
        if self._pool:
            self._pool.shutdown()
            self._pool = None
