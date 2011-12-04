from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log


class XvfbSetup(ClusterSetup):
    """
    Installs, configures, and sets up a Xvfb server
    Thanks to Adam Marsh for his contribution
    """
    def run(self, nodes, master, user, user_shell, volumes):
        for node in nodes:
            log.info("Installing Xvfb on %s" % node.alias)
            node.ssh.execute('apt-get -y install xvfb')
            log.info("Launching Xvfb Server on %s" % node.alias)
            node.ssh.execute('screen -d -m Xvfb :1 -screen 0 1024x768x16')
            profile = node.ssh.remote_file('/etc/profile', 'a')
            profile.write('\nexport DISPLAY=":1"\n')
            profile.close()
