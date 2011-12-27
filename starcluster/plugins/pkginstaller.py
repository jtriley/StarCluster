# Copyright 2010 Austin Godber <godber@uberhip.com>
#
# This program is distributed under the terms of the Lesser GNU General Public
# License

from starcluster import clustersetup

from starcluster.logger import log


class PackageInstaller(clustersetup.DefaultClusterSetup):
    """
    NOTE: This plugin assumes that /home is an EBS volume.

    WARNING: This will upgrade any packages that are out of date. So you might
    end up with slightly different builds of packages.

    Loads a list of packages out of the /home/.starcluster-packages file. This
    file is a dselect package list and can be managed manually.  A new command
    called ``cluster-install`` will be installed to help automatically manage
    this file while also installing the packages on all nodes.
    """
    def __init__(self):
        super(PackageInstaller, self).__init__()
        self.pkgfile = '/home/.starcluster-packages'

    def _deselect_upgrade(self, node):
        node.ssh.execute('dpkg --set-selections < ' + self.pkgfile)
        node.apt_command('update')
        node.apt_command('dselect-upgrade')

    def run(self, nodes, master, user, user_shell, volumes):
        mconn = master.ssh
        if mconn.isfile(self.pkgfile):
            log.info("Package file found at: %s" % self.pkgfile)
            log.info("Installing packages on all nodes")
            for node in nodes:
                self.pool.simple_job(self._deselect_upgrade, (node),
                                     jobid=node.alias)
            self.pool.wait(len(nodes))
        else:
            log.info("No package file found at: %s" % self.pkgfile)
        cluster_install = "/usr/bin/cluster-install"
        if not mconn.isfile(cluster_install):
            log.info("Installing cluster-install utility")
            f = mconn.remote_file(cluster_install, 'w')
            f.write(cluster_install_tmpl)
            f.chmod(0755)
            f.close()
        else:
            log.info("cluster-install utility is already installed...")


cluster_install_tmpl = """
#!/bin/bash
# Copyright 2010 Austin Godber <godber@uberhip.com>
#
# This program is distributed under the terms of the Lesser GNU General Public
# License

set -e -u

PACKAGE_FILE="/home/.starcluster-packages"

function error_msg() {
    msg=$1
    if [ -n "${msg}" ]; then
        echo
        echo "ERROR: ${msg}"
    fi
}

function die () {
    error_msg "${1}"
    exit
}

function usage () {
    error_msg "${1}"
    cat <<END

This is a wrapper for apt-get that installs packages on all nodes and stores
the list of packages for future use.

Usage:

    cluster-install package1 [package2 package3 ...]

END
    exit
}

# Must be root
if [ `id -u` != 0 ];
then
    echo "You must be root or use sudo to execute this script."
    exit
fi

packages=$@
if [ -z "${packages}" ]; then
    usage "You must provide a package to install"
fi

# generate list of nodes from /etc/hosts, excluding the master
nodelist=`grep node /etc/hosts | awk '{print $4}'`

# Install packages on Master
apt-get update || die "Failed to run apt-get update"
apt-get -y install ${packages} || die "Failed installing packages: ${packages}"

# Install packages on Nodes
for i in $nodelist
do
   ssh $i apt-get update
   ssh $i apt-get -y install ${packages}
done

# Record packages on Master
# assuming that /home/ is a persistent EBS volume
dpkg --get-selections > $PACKAGE_FILE || die "Failed to save packages"
"""
