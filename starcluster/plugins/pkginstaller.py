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

    def on_add_node(self, new_node, nodes, master, user, user_shell, volumes):
        log.info('Installing the following packages on %s:' % new_node.alias)
        pkgs = ' '.join(self.packages)
        new_node.apt_install(pkgs)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")
