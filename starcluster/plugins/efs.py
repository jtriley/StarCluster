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
import botocore.exceptions

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

    def on_shutdown(self, nodes, master, user, user_shell, volumes):
        """
        This method gets executed before shutting down the cluster
        """
        self._nodes = nodes
        self._master = master
        self._user = user
        self._user_shell = user_shell
        self._volumes = volumes

        # I'd like to modify_mount_target_security_groups() with an
        # empty list, but that doesn't seem to be allowed.  instead
        # we'll associate with one of the default groups.  however
        # there will probably be more than one, and I don't have the
        # VPC ID handy to pick the right one. So I'll get all of the
        # default groups here, and try each and stop when we find one
        # that works.

        default_security_groups = master.ec2.get_security_groups(filters={'group-name': 'default'})

        # this is dependent on the config file using a dns, instead of
        # an IP. a future version should be robust for both forms
        parts = self.dns_name.split('.')
        filesystem = parts[1]

        b3client = boto3.client('efs')

        # we need a MountTargetId later, use this to determine it.
        # notice this is copy and pasted with the same logic found in
        # _authorize_efs. It would perhaps be better to break it into
        # a function to be called from both places.

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

        # we now have our MountTargetId, try to assign it to each of
        # the default security groups, and stop when one of them works
        if mount_target_id:
            log.info('Deauthorizing EFS security group, by reassociating with default')
            successfully_reassigned = None
            for a_default_sg in default_security_groups:
                try:
                    b3client.modify_mount_target_security_groups(
                        MountTargetId=mount_target_id,
                        SecurityGroups=[a_default_sg.id],
                    )
                    successfully_reassigned = True
                    break
                except botocore.exceptions.ClientError:
                    # couldn't reassociate, probably in wrong vpc
                    pass
            return successfully_reassigned
        return True



    def _authorize_efs(self, master):

        # this is dependent on the config file using a dns, instead of
        # an IP. a future version should be robust for both forms
        parts = self.dns_name.split('.')
        filesystem = parts[1]

        b3client = boto3.client('efs')

        # we need a MountTargetId later, use this to determine it.
        # notice this is copy and pasted with the same logic found in
        # _authorize_efs. It would perhaps be better to break it into
        # a function to be called from both places.

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
            b3client.modify_mount_target_security_groups(
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
