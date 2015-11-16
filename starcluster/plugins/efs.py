# Copyright 2015 Michael Cariaso
#
# This file is a plugin for StarCluster.
#
# This EFS plugin is free software: you can redistribute it and/or modify it under
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
import boto3

class EFSPlugin(clustersetup.DefaultClusterSetup):
    """Add EFS support

    Example config:

    [plugin efs]
    SETUP_CLASS = efs.EFSPlugin
    mount_point = /mnt/myefs
    dns_name = us-west-2a.fs-1234abcd.efs.us-west-2.amazonaws.com

    """

    def __init__(self, mount_point=None, dns_name=None,
                 **kwargs):
        self.mount_point = mount_point
        self.dns_name = dns_name
        super(EFSPlugin, self).__init__(**kwargs)

    def run(self, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Configuring EFS...")
        if self._authorize_efs(master):
            log.info("Installing nfs on all nodes")
            for node in nodes:
                self._install_efs_on_node(node)

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("Adding %s to EFS" % node.alias)
        self._install_efs_on_node(node)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes
        log.info("No need to remove %s from EFS" % node.alias)

    def _authorize_efs(self, master):
        parts = self.dns_name.split('.')
        filesystem = parts[1]

        b3client = boto3.client('efs')

        mount_target_id = None
        mtresponse = b3client.describe_mount_targets(FileSystemId=filesystem)
        for mt in mtresponse.get('MountTargets'):
            subnetid = mt.get('SubnetId')
            if subnetid == master.subnet_id:
                mount_target_id = mt.get('MountTargetId')
                break
        else:
            log.info('correct subnet not found')
            return False

        if mount_target_id:
            log.info('Authorizing EFS security group')
            sgresponse = b3client.modify_mount_target_security_groups(
                MountTargetId=mount_target_id,
                SecurityGroups=[master.cluster_groups[0].id],
            )
            return True
        return False

    def _install_efs_on_node(self, node):
        log.info("Installing nfs on %s" % node.alias)

        # in theory this is needed, but in practice it is already installed
        # and running this apt_install causes a crash
        #node.apt_install('nfs-common')

        if not node.ssh.isdir(self.mount_point):
            node.ssh.mkdir(self.mount_point)
        cmd = 'mount -t nfs4 %s:/ %s' % (self.dns_name, self.mount_point)
        log.info("run: %s" % cmd)
        node.ssh.execute(cmd)
