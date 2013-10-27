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

"""Install python packages using pip

Packages are downloaded/installed in parallel, allowing for faster installs
when using many nodes.

For example to install the flask and SQLAlchemy packages on all the nodes::

    [plugin webapp-packages]
    setup_class = starcluster.plugins.pypkginstaller.PyPkgInstaller
    packages = flask, SQLAlchemy

It can also be used to install the development version of packages from
github, for instance if you want to install the master branch of IPython
and the latest released version of some dependencies::

    [plugin ipython-dev]
    setup_class = starcluster.plugins.pypkginstaller.PyPkgInstaller
    install_cmd = pip install -U %s
    packages = pyzmq,
               python-msgpack,
               git+http://github.com/ipython/ipython.git

"""
from starcluster.clustersetup import DefaultClusterSetup
from starcluster.logger import log
from starcluster.utils import print_timing


class PyPkgInstaller(DefaultClusterSetup):
    """Install Python packages with pip."""

    def __init__(self, packages="", install_command="pip install %s"):
        super(PyPkgInstaller, self).__init__()
        self.install_command = install_command
        self.packages = [p.strip() for p in packages.split(",") if p.strip()]

    @print_timing("PyPkgInstaller")
    def install_packages(self, nodes, dest='all nodes'):
        log.info("Installing Python packages on %s:" % dest)
        commands = [self.install_command % p for p in self.packages]
        for command in commands:
            log.info("$ " + command)
        cmd = "\n".join(commands)
        for node in nodes:
            self.pool.simple_job(node.ssh.execute, (cmd,), jobid=node.alias)
        self.pool.wait(len(nodes))

    def run(self, nodes, master, user, user_shell, volumes):
        self.install_packages(nodes)

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self.install_packages([node], dest=node.alias)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        raise NotImplementedError("on_remove_node method not implemented")
