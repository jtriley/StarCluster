# Copyright 2015 Michael Cariaso
#
# This file is a plugin for StarCluster.
#
# This plugin is free software: you can redistribute it and/or modify it under
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
        self._master = master
        self._new_security_group = master.cluster_groups[0].id

        log.info("Configuring EFS for %s" % self._new_security_group)
        self._authorize_efs()
        log.info("Installing nfs on all nodes")
        for node in nodes:
            log.info("  Installing nfs on %s" % node)
            self._install_efs_on_node(node)

    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        self._master = master
        self._new_security_group = node.cluster_groups[0].id

        log.info("Adding %s to EFS" % node.alias)
        self._install_efs_on_node(node)

    def on_remove_node(self, node, nodes, master, user, user_shell, volumes):
        self._master = master
        log.info("No need to remove %s from EFS" % node.alias)

    def on_shutdown(self, nodes, master, user, user_shell, volumes):
        """
        This method gets executed before shutting down the cluster
        """
        self._master = master
        self._new_security_group = master.cluster_groups[0].id

        self._deauthorize_efs()

    def _get_efs_client(self):
        creds = self._master.ec2.__dict__
        b3client = boto3.client(
            'efs',
            aws_access_key_id=creds.get('aws_access_key_id'),
            aws_secret_access_key=creds.get('aws_secret_access_key'),
            region_name=creds.get('_conn').region.name,
        )
        return b3client

    def _authorize_efs(self):

        # this is dependent on the config file using a dns, instead of
        # an IP. a future version should be robust for both forms
        parts = self.dns_name.split('.')
        filesystem = parts[1]

        self._b3client = self._get_efs_client()

        mount_targets = self._get_mount_targets(filesystem)

        for targetinfo in mount_targets:
            log.info('Authorizing EFS security group')
            resp = self._b3client.describe_mount_target_security_groups(
                MountTargetId=targetinfo.get('MountTargetId'),
            )
            oldgroups = resp['SecurityGroups']
            oldgroups.append(self._new_security_group)
            newgroups = list(set(oldgroups))

            self._b3client.modify_mount_target_security_groups(
                MountTargetId=targetinfo.get('MountTargetId'),
                SecurityGroups=newgroups,
            )

    def _deauthorize_efs(self):

        # this is dependent on the config file using a dns, instead of
        # an IP. a future version should be robust for both forms
        parts = self.dns_name.split('.')
        filesystem = parts[1]

        self._b3client = self._get_efs_client()

        mount_targets = self._get_mount_targets(filesystem)

        for targetinfo in mount_targets:
            log.info('Authorizing EFS security group')
            resp = self._b3client.describe_mount_target_security_groups(
                MountTargetId=targetinfo.get('MountTargetId'),
            )
            groups = resp['SecurityGroups']
            found_group = None
            try:
                groups.remove(self._new_security_group)
                found_group = True
            except ValueError, e:
                log.info('Expected security group is not currently associated')
                found_group = False

            if found_group:
                self._b3client.modify_mount_target_security_groups(
                    MountTargetId=targetinfo.get('MountTargetId'),
                    SecurityGroups=groups,
                )
                msg = 'Disassociated EFS security group %s' % (
                    self._new_security_group
                )
                log.info(msg)

    def _get_mount_targets(self, filesystem):
        mtresponse = self._b3client.describe_mount_targets(
            FileSystemId=filesystem)
        mts = mtresponse.get('MountTargets')
        return mts

    def _install_efs_on_node(self, node):
        node.ssh.switch_user('root')
        node.ssh.makedirs(self.mount_point, mode=0755)

        parts = self.dns_name.split('.')
        get_info_url = 'http://169.254.169.254/latest/meta-data/'
        get_az_url = '%splacement/availability-zone' % get_info_url
        cmd = 'mount -t nfs4 -ominorversion=1 $(curl -s %s).%s:/ %s' % (
            get_az_url, '.'.join(parts[1:]), self.mount_point)
        node.ssh.execute(cmd)
