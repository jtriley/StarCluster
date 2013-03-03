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
