from starcluster.clustersetup import DefaultClusterSetup
from starcluster.logger import log


class XvfbSetup(DefaultClusterSetup):
    """
    Installs, configures, and sets up an Xvfb server
    (thanks to Adam Marsh for his contribution)
    """
    def _install_xvfb(self, node):
        node.apt_install('xvfb')

    def _launch_xvfb(self, node):
        node.ssh.execute('screen -d -m Xvfb :1 -screen 0 1024x768x16')
        profile = node.ssh.remote_file('/etc/profile.d/scxvfb.sh', 'w')
        profile.write('export DISPLAY=":1"')
        profile.close()

    def run(self, nodes, master, user, user_shell, volumes):
        log.info("Installing Xvfb on all nodes")
        for node in nodes:
            self.pool.simple_job(self._install_xvfb, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Launching Xvfb Server on all nodes")
        for node in nodes:
            self.pool.simple_job(self._launch_xvfb, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        #self._terminate(nodes)

    def _terminate(self, nodes):
        for node in nodes:
            self.pool.simple_job(node.ssh.execute, ('pkill Xvfb'),
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
