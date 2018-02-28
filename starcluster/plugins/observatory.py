# Copyright 2017 Daniel Treiman
#

from starcluster import clustersetup
from starcluster.logger import log
from starcluster.templates import observatory


class ObservatoryPlugin(clustersetup.ClusterSetup):
    """Installs and launches a starcluster GUI as a service.

    Prior to using this, a starcluster config must be installed at /etc/starcluster/config on the master AMI.
    Any private keys required by the config must also be installed and have the correct permissions.
    """
    STARCLUSTER_CONFIG_DIR = '/etc/starcluster'
    INSTALLER_PATH = '/tmp/install_starcluster_observatory.bash'
    API_SERVICE_PATH = '/etc/systemd/system/observatory_api.service'
    LOAD_BALANCER_SERVICE_PATH = '/etc/systemd/system/observatory_load_balancer.service'
    DASHBOARD_SERVICE_PATH = '/etc/systemd/system/observatory_dashboard.service'

    def __init__(self, instance_types='c4.large,p2.xlarge,p3.2xlarge', load_balance=True, **kwargs):
        """Constructor.

        Args:
            instance_types (string) - Comma-separated list of approved instance types.
        """
        super(ObservatoryPlugin, self).__init__(**kwargs)
        self.instance_types = instance_types
        self.load_balance = load_balance

    def _install_server(self):
        """Installs observatory and services on master."""
        master = self._master
        # Install starcluster and starcluster-observatory on remote
        log.info('Running install script')
        install_script = master.ssh.remote_file(self.INSTALLER_PATH, 'w')
        install_script.write(observatory.install_script)
        install_script.close()
        master.ssh.execute('/bin/bash %s && rm %s' % (self.INSTALLER_PATH, self.INSTALLER_PATH))
        # Install service definitions
        log.info('Configuring services')
        api_service = master.ssh.remote_file(self.API_SERVICE_PATH, 'w')
        cluster_name = master.alias.split('-')[0]  # Hack
        api_service.write(observatory.api_service_template % (cluster_name))
        api_service.close()

        load_balancer_service = master.ssh.remote_file(self.LOAD_BALANCER_SERVICE_PATH, 'w')
        load_balancer_service.write(observatory.load_balancer_service_template)
        load_balancer_service.close()

        dashboard_service = master.ssh.remote_file(self.DASHBOARD_SERVICE_PATH, 'w')
        dashboard_service.write(observatory.dashboard_service_template % (self.instance_types))
        dashboard_service.close()

    def _setup_observatory_master(self):
        """Configure observatory master."""
        self._install_server()
        # Start services
        log.info('Starting services')
        self._master.ssh.execute('systemctl start observatory_api && systemctl start observatory_dashboard')
        if self.load_balance:
            self._master.ssh.execute('systemctl start observatory_load_balancer')

    def run(self, nodes, master, user, user_shell, volumes):
        if not master.ssh.isdir(self.STARCLUSTER_CONFIG_DIR):
            log.error('No starcluster config directory (/etc/starcluster), skipping...')
            return
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        self._setup_observatory_master()
