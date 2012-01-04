from starcluster import optcomplete
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
            return optcomplete.ListCompleter(completion_list)
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
            return optcomplete.ListCompleter(compl_list)
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
            return optcomplete.ListCompleter(completion_list)
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
            return optcomplete.ListCompleter(completion_list)
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
            return optcomplete.ListCompleter(completion_list)
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
            return optcomplete.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)


class VolumeCompleter(Completer):
    """
    Returns a list of all volume ids as completion options
    """
    def _completer(self):
        try:
            completion_list = [v.id for v in self.ec2.get_volumes()]
            return optcomplete.ListCompleter(completion_list)
        except Exception, e:
            log.error('something went wrong fix me: %s' % e)
