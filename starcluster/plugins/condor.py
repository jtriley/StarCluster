from starcluster import clustersetup
from starcluster.templates import condor
from starcluster.logger import log

CONDOR_CFG = '/etc/condor/condor_config'


class CondorPlugin(clustersetup.DefaultClusterSetup):

    def _add_condor_node(self, node):
        condorcfg = node.ssh.remote_file(CONDOR_CFG, 'w')
        daemon_list = "MASTER, STARTD, SCHEDD"
        if node.is_master():
            daemon_list += ", COLLECTOR, NEGOTIATOR"
        condorcfg.write(condor.condor_tmpl % dict(DAEMON_LIST=daemon_list))
        condorcfg.close()
        node.ssh.execute('pkill condor', ignore_exit_status=True)
        node.ssh.execute('/etc/init.d/condor start')

    def _setup_condor(self, master=None, nodes=None):
        log.info("Setting up Condor grid")
        master = master or self._master
        nodes = nodes or self.nodes
        log.info("Starting Condor master")
        self._add_condor_node(master)
        log.info("Starting Condor nodes")
        for node in nodes:
            self.pool.simple_job(self._add_condor_node, (node,),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def run(self, nodes, master, user, user_shell, volumes):
        try:
            self._nodes = nodes
            self._master = master
            self._user = user
            self._user_shell = user_shell
            self._volumes = volumes
            self._setup_condor()
        finally:
            self.pool.shutdown()

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Adding %s to Condor" % node.alias)
        self._add_condor_node(node)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Removing %s from Condor peacefully..." % node.alias)
        master.ssh.execute("condor_off -peaceful %s" % node.alias)
        node.ssh.execute("pkill condor" % node.alias, ignore_exit_status=True)
