from starcluster import clustersetup
from starcluster.logger import log


class PackageInstaller(clustersetup.DefaultClusterSetup):
    """
    This plugin installs Ubuntu packages on all nodes in the cluster. The
    packages are specified in the plugin's config:

    [plugin pkginstaller]
    setup_class = starcluster.plugins.pkginstaller.PackageInstaller
    packages = mongodb, python-mongodb
    """
    def __init__(self, packages=None):
        super(PackageInstaller, self).__init__()
        self.packages = packages
        if packages:
            self.packages = [pkg.strip() for pkg in packages.split(',')]

    def run(self, nodes, master, user, user_shell, volumes):
        if not self.packages:
            log.info("No packages specified!")
            return
        log.info('Installing the following packages on all nodes:')
        log.info(', '.join(self.packages), extra=dict(__raw__=True))
        pkgs = ' '.join(self.packages)
        for node in nodes:
            self.pool.simple_job(node.apt_install, (pkgs), jobid=node.alias)
        self.pool.wait(len(nodes))
