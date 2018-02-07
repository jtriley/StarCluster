# Copyright 2017 Daniel Treiman
#

from starcluster import clustersetup
from starcluster.logger import log
from starcluster.templates import observatory


class ObservatoryPlugin(clustersetup.DefaultClusterSetup):
    """Installs and launches a starcluster GUI as a service.

    Prior to using this, a starcluster config must be installed at /etc/starcluster/config on the master AMI.
    Any private keys required by the config must also be installed and have the correct permissions.
    """
    INSTALLER_PATH = '/tmp/install_starcluster_observatory.bash'
    API_SERVICE_PATH = '/etc/systemd/system/observatory_api.service'
    DASHBOARD_SERVICE_PATH = '/etc/systemd/system/observatory_dashboard.service'

    def __init__(self, starcluster_config=None, key_file=None, **kwargs):
        """Constructor.

        Args:
        """
        super(ObservatoryPlugin, self).__init__(**kwargs)

    def _install_server(self):
        """Installs observatory and services on master."""
        master = self._master
        # Install starcluster and starcluster-observatory on remote
        install_script = master.ssh.remote_file(self.INSTALLER_PATH, 'w')
        install_script.write(observatory.install_script)
        install_script.close()
        master.ssh.execute('/bin/bash %s && rm %s' % (self.INSTALLER_PATH, self.INSTALLER_PATH))
        # Install starcluster configuration and private key

        # Install service definitions
        api_service = master.ssh.remote_file(self.API_SERVICE_PATH, 'w')
        api_service.write(observatory.api_service)
        api_service.close()
        dashboard_service = master.ssh.remote_file(self.DASHBOARD_SERVICE_PATH, 'w')
        dashboard_service.write(observatory.dashboard_service)
        dashboard_service.close()

    def _setup_observatory_master(self, master):
        """Configure observatory master."""
        self._install_server()
        # Start services
        self._master.ssh.execute('systemctl start observatory_api && systemctl start observatory_dashboard')

    def run(self, nodes, master, user, user_shell, volumes):
        self._master = master
        self._setup_observatory_master()

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._master = master
