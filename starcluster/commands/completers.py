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

from starcluster import completion
from starcluster.logger import log

from base import CmdBase


class Completer(CmdBase):
    """
    Base class for all completer classes
    """

    @property
    def completer(self):
        return self._completer()


class ClusterCompleter(Completer):
    """
    Returns a list of all cluster names as completion options
    """
    def _completer(self):
        try:
            cm = self.cm
            clusters = cm.get_cluster_security_groups()
            completion_list = [cm.get_tag_from_sg(sg.name)
                               for sg in clusters]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class NodeCompleter(Completer):
    """
    Returns a list of all node names as completion options
    """
    def _completer(self):
        try:
            cm = self.cm
            clusters = cm.get_cluster_security_groups()
            compl_list = [cm.get_tag_from_sg(sg.name) for sg in clusters]
            max_num_nodes = 0
            for scluster in clusters:
                num_instances = len(scluster.instances())
                if num_instances > max_num_nodes:
                    max_num_nodes = num_instances
            compl_list.extend(['master'])
            compl_list.extend([str(i) for i in range(0, num_instances)])
            compl_list.extend(["node%03d" % i
                               for i in range(1, num_instances)])
            return completion.ListCompleter(compl_list)
        except Exception, e:
            print e
            log.error('something went wrong fix me: %s' % e)


class ImageCompleter(Completer):
    """
    Returns a list of all registered image ids as completion options
    """
    def _completer(self):
        try:
            rimages = self.ec2.registered_images
            completion_list = [i.id for i in rimages]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class EBSImageCompleter(Completer):
    """
    Returns a list of all registered EBS image ids as completion options
    """
    def _completer(self):
        try:
            rimages = self.ec2.registered_images
            completion_list = [i.id for i in rimages if
                               i.root_device_type == "ebs"]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class S3ImageCompleter(Completer):
    """
    Returns a list of all registered S3 image ids as completion options
    """
    def _completer(self):
        try:
            rimages = self.ec2.registered_images
            completion_list = [i.id for i in rimages if
                               i.root_device_type == "instance-store"]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class InstanceCompleter(Completer):
    """
    Returns a list of all instance ids as completion options
    """
    show_dns_names = False

    def _completer(self):
        try:
            instances = self.ec2.get_all_instances()
            completion_list = [i.id for i in instances]
            if self.show_dns_names:
                completion_list.extend([i.dns_name for i in instances])
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class VolumeCompleter(Completer):
    """
    Returns a list of all volume ids as completion options
    """
    def _completer(self):
        try:
            completion_list = [v.id for v in self.ec2.get_volumes()]
            return completion.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)
