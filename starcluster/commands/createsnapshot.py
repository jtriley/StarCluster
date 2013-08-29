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

import os

from starcluster import static
from starcluster import exception

from base import CmdBase

class CmdCreateSnapshot(CmdBase):
    """
    createsnapshot [options] (<volume_name>|<volume_id>)

    Create an EBS snapshot from an EBS volume
    """

    names = ['createsnapshot', 'cs']

    def addopts(self, parser):
        parser.add_option(
            "-n", "--name", dest="name", action="store", type="string",
            default=None, help="Give the snapshot a user-friendly name "
            "(default is the name of the volume)")
        parser.add_option(
            "-d", "--description", dest="description", action="store", type="string",
            default=None, help="Give the snapshot a description "
            "(default is derived from the volume name)")
        parser.add_option(
            "-t", "--tag", dest="tags", action="callback", type="string",
            default={}, callback=self._build_dict,
            help="One or more tags to apply to the new snapshot (key=value)")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error(
                "you must specify a volume id or name")
        (name,) = args

        by_id = False
        snapshot_name = self.opts.name

        vols = self.ec2.get_volumes()
        vol = filter(lambda v: v.id == name, vols)
        if vol:
            vol = vol.pop()
            self.log.info('Found volume by id: %s' % name)
            if 'Name' in vol.tags:
                snapshot_name = snapshot_name or vol.tags['Name']
            by_id = True
        else:
            vol = filter(lambda v: 'Name' in v.tags and v.tags['Name'] == name, vols)
            if vol:
                self.log.info('Found volume by name: %s' % name)
                vol = vol.pop()
                snapshot_name = snapshot_name or name
            else:
                raise exception.VolumeDoesNotExist(name)

        if not snapshot_name:
            raise ValueError(
                'Volume %s has no name associated with it.  Please provide a name.' % vol.id)

        description = self.opts.description or "Snapshot created from volume %s" % name

        if by_id:
            find_snapshot = self.ec2.get_snapshots(volume_ids = [name])
        else:
            find_snapshot = self.ec2.get_snapshots(filters = {'tag:Name': snapshot_name})

        if find_snapshot:
            find_snapshot = find_snapshot.pop()
            raise ValueError('Already found snapshot with matching volume id/name %s: %s'
                             % (name, find_snapshot.id))

        snapshot = self.ec2.create_snapshot(
            vol, description=description, wait_for_snapshot=False)

        for (k, v) in self.opts.tags.iteritems():
            snapshot.add_tag(k, v)

        snapshot.add_tag('Name', snapshot_name)
        snapshot.update()

        self.log.info('Creating snapshot %s with tags: %s' % (snapshot.id, str(snapshot.tags)))
