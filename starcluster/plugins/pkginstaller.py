# Copyright 2010 Austin Godber <godber@uberhip.com>
#
# This program is distributed under the terms of the Lesser GNU General Public
# License

from starcluster import clustersetup

from starcluster.logger import log


class PackageInstaller(clustersetup.ClusterSetup):
    """
    NOTE: This plugin assumes that /home is an EBS volume.

    WARNING: This will upgrade any packages that are out of date. So you might
    end up with slightly different builds of packages.

    Loads a list of packages out of the /home/.starcluster-packages file. This
    file is a dselect package list and can be managed manually.  A new command
    called ``cluster-install`` will be installed to help automatically manage
    this file while also installing the packages on all nodes.
    """

    def run(self, nodes, master, user, user_shell, volumes):
        log.info('Running PackageInstaller plugin.')
        pkgfile = '/home/.starcluster-packages'
        mconn = master.ssh
        # Test for the package file on the master node
        if mconn.path_exists(pkgfile):
            log.info("[PackageInstaller] Package file found at: %s" % pkgfile)
            for node in nodes:
                log.info(
                    "[PackageInstaller] Installing packages on %s" %
                    node.alias)
                node.ssh.execute('dpkg --set-selections < ' + pkgfile)
                node.ssh.execute(
                    'apt-get update && apt-get -y dselect-upgrade')
        else:
            log.info("[PackageInstaller] No package file found at: %s" %
                     pkgfile)
        cluster_install = "/usr/bin/cluster-install"
        if not mconn.path_exists(cluster_install):
            log.info("[PackageInstaller] Installing cluster-install utility")
            f = mconn.remote_file(cluster_install, 'w')
            f.write(cluster_install_tmpl)
            f.close()
            f.chmod(0755, cluster_install)


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
# assuming that /home/ is a persistant EBS volume
dpkg --get-selections > $PACKAGE_FILE || die "Failed to save packages"
"""
