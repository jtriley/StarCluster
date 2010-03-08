import os
import sys
import unittest
import tempfile
from starcluster.logger import log
from starcluster.exception import ClusterValidationError, PluginError
from starcluster.tests import StarClusterTest
from starcluster.tests.templates.config import config_test_template, default_config

class TestClusterValidation(StarClusterTest):

    def test_aws_credentials_validation(self):
        ec2 = self.config.get_easy_ec2()
        cluster = self.config.get_cluster('c1')
        try:
            cluster._validate_credentials()
        except ClusterValidationError,e:
            pass
        else:
            raise Exception("cluster allows invalid aws credentials")

    def test_plugin_loading(self):
        # default test template should have valid plugins by default
        cluster = self.config.get_cluster('c1')
        # make them invalid
        cases = [
            {'p1_class': 'None'}, 
            {'p1_class':'unittest.TestCase'},
        ]
        for case in cases:
            cfg = self.get_custom_config(**case)
            try:
                cluster = cfg.get_cluster('c1')
            except PluginError,e:
                pass
            else:
                raise Exception(
                    'cluster allows non-valid plugin setup class (case: %s)' %
                    case)

    def test_cluster_size_validation(self):
        cases = [
            {'c1_size': -1}, 
            {'c1_size': 0}
        ]
        for case in cases:
            cfg = self.get_custom_config(**case)
            try:
                cluster = cfg.get_cluster('c1')
                cluster._validate_cluster_size()
            except ClusterValidationError,e:
                pass
            else:
                raise Exception('cluster allows invalid cluster size (case: %s)'
                               % case)

    def test_shell_validation(self):
        cases = [
            {'c1_shell': ''}, 
            {'c1_shell': 'nosh'}, 
            {'c1_shell': 2}
        ]
        for case in cases:
            cfg = self.get_custom_config(**case)
            try:
                cluster = cfg.get_cluster('c1')
                cluster._validate_shell_setting()
            except ClusterValidationError,e:
                pass
            else:
                raise Exception('cluster allows invalid cluster shell (case: %s)'
                               % case)

    def test_keypair_validation(self):
        tmpfile = tempfile.NamedTemporaryFile()
        tmp_file = tmpfile.name
        tmpfile.close()
        tmpdir = tempfile.mkdtemp()
        cases = [{'k1_location': tmp_file}, {'k1_location':tmpdir}]
        for case in cases:
            cfg = self.get_custom_config(**case)
            cluster = cfg.get_cluster('c1')
            try:
                cluster._validate_keypair()
            except ClusterValidationError,e:
                pass
            else:
                raise Exception('cluster allows invalid key_location')
        os.rmdir(tmpdir)

    def __test_for_validation_error(self, cases, test, cluster_name='c1'):
        for case in cases:
            cfg = self.get_custom_config(**case)
            cluster = cfg.get_cluster(cluster_name)
            try:
                getattr(cluster,test)()
            except ClusterValidationError,e:
                pass
            else:
                return case

    def test_instance_type_validation(self):
        cases = [
            {'c1_node_type': None}, 
            {'c1_master_type': None},
            {'c1_node_type': 'asdfa'},
            {'c1_master_type': 'asdfa'},
            {'c1_zone': None},
        ]
        failed = self.__test_for_validation_error(cases, '_validate_instance_types')
        if failed:
            raise Exception('cluster allows invalid instance type setttings (case: %s)' % failed)

    def test_ebs_validation(self):
        cases = [
            {'v1_id': 'asdfa2'},
            {'v1_device': '/dev/asd'},
            {'v1_partition': '/dev/asd1'},
            {'v1_mount_path': 'home'},
            {'v1_device': '/dev/sda', 'v1_partition': '/dev/sdb1'},
        ]
        failed = self.__test_for_validation_error(cases, '_validate_ebs_settings')
        if failed:
            raise Exception('cluster allows invalid ebs settings (case: %s)' % failed)

    def test_image_validation(self):
        pass

    def test_zone_validation(self):
        pass

    def test_platform_validation(self):
        pass

