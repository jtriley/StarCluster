import os
import copy
import tempfile

import logging
logging.disable(logging.WARN)

from starcluster import exception
from starcluster import tests
from starcluster import static
from starcluster import config
from starcluster import utils


class TestStarClusterConfig(tests.StarClusterTest):

    def test_valid_config_template(self):
        self.config

    def test_config_dne(self):
        tmp_file = tempfile.NamedTemporaryFile()
        non_existent_file = tmp_file.name
        tmp_file.close()
        assert not os.path.exists(non_existent_file)
        try:
            config.StarClusterConfig(non_existent_file, cache=True).load()
        except exception.ConfigNotFound:
            pass
        else:
            raise Exception('config loaded non-existent config file %s' %
                            non_existent_file)

    def test_get_cluster(self):
        try:
            self.config.get_cluster_template('no_such_cluster')
        except exception.ClusterTemplateDoesNotExist:
            pass
        else:
            raise Exception('config returned non-existent cluster')

    def test_int_required(self):
        cases = [{'c1_size':'-s'}, {'c1_size': 2.5}, {'v1_partition': 'asdf'},
                 {'v1_partition': 0.33}]
        for case in cases:
            try:
                self.get_custom_config(**case)
            except exception.ConfigError:
                pass
            else:
                raise Exception('config is not enforcing ints correctly')

    def test_bool_required(self):
        cases = [{'enable_experimental': 2}]
        for case in cases:
            try:
                self.get_custom_config(**case)
            except exception.ConfigError:
                pass
            else:
                raise Exception("config is not enforcing strs correctly")

    def test_missing_required(self):
        cfg = self.config._config
        section_copy = copy.deepcopy(cfg._sections)
        for setting in static.CLUSTER_SETTINGS:
            if not static.CLUSTER_SETTINGS[setting][1]:
                continue
            del cfg._sections['cluster c1'][setting]
            try:
                self.config.load()
            except exception.ConfigError:
                pass
            else:
                raise Exception(
                    "config is not enforcing required setting '%s'" % setting)
            cfg._sections = copy.deepcopy(section_copy)

    def test_volumes(self):
        c1 = self.config.get_cluster_template('c1')
        vols = c1.volumes
        assert len(vols) == 3
        assert 'v1' in vols
        v1 = vols['v1']
        assert 'volume_id' in v1 and v1['volume_id'] == 'vol-c999999'
        assert 'device' in v1 and v1['device'] == '/dev/sdj'
        assert 'partition' in v1 and v1['partition'] == '/dev/sdj1'
        assert 'mount_path' in v1 and v1['mount_path'] == '/volume1'
        assert 'v2' in vols
        v2 = vols['v2']
        assert 'volume_id' in v2 and v2['volume_id'] == 'vol-c888888'
        assert 'device' in v2 and v2['device'] == '/dev/sdk'
        assert 'partition' in v2 and v2['partition'] == '/dev/sdk1'
        assert 'mount_path' in v2 and v2['mount_path'] == '/volume2'
        assert 'v3' in vols
        v3 = vols['v3']
        assert 'volume_id' in v3 and v3['volume_id'] == 'vol-c777777'
        assert 'device' in v3 and v3['device'] == '/dev/sdl'
        assert 'partition' in v3 and v3['partition'] == '/dev/sdl1'
        assert 'mount_path' in v3 and v3['mount_path'] == '/volume3'

    def test_volume_not_defined(self):
        try:
            self.get_custom_config(**{'c1_vols': 'v1,v2,v2323'})
        except exception.ConfigError:
            pass
        else:
            raise Exception(
                'config allows non-existent volumes to be specified')

    def test_clusters(self):
        assert 'c1' in self.config.clusters
        assert 'c2' in self.config.clusters
        assert 'c3' in self.config.clusters

    def test_extends(self):
        c1 = self.config.clusters.get('c1')
        c2 = self.config.clusters.get('c2')
        c3 = self.config.clusters.get('c3')
        c2_settings = ['__name__', 'extends', 'keyname', 'key_location',
                       'cluster_size', 'node_instance_type',
                       'master_instance_type', 'volumes']
        c3_settings = ['__name__', 'extends', 'keyname', 'key_location',
                       'cluster_size', 'volumes']
        for key in c1:
            if key in c2 and not key in c2_settings:
                assert c2[key] == c1[key]
            else:
                # below only true for default test config
                # not required in general
                assert c2[key] != c1[key]
        for key in c2:
            if key in c3 and not key in c3_settings:
                assert c3[key] == c2[key]
            else:
                # below only true for default test config
                # not required in general
                assert c3[key] != c2[key]

    def test_order_invariance(self):
        """
        Loads all cluster sections in the test config in all possible orders
        (i.e. c1,c2,c3, c3,c1,c2, etc.) and test that the results are the same
        """
        cfg = self.config
        orig = cfg.clusters
        cfg.clusters = None
        sections = cfg._get_sections('cluster')
        for perm in utils.permute(sections):
            new = cfg._load_cluster_sections(perm)
            assert new == orig

    def test_plugins(self):
        c1 = self.config.get_cluster_template('c1')
        plugs = c1.plugins
        assert len(plugs) == 3
        plugs = self.config.clusters.c1.plugins
        # test that order is preserved
        p1 = plugs[0]
        p2 = plugs[1]
        p3 = plugs[2]
        assert p1['__name__'] == 'p1'
        assert p1['setup_class'] == 'starcluster.tests.mytestplugin.SetupClass'
        assert p1['my_arg'] == '23'
        assert p1['my_other_arg'] == 'skidoo'
        assert p2['__name__'] == 'p2'
        setup_class2 = 'starcluster.tests.mytestplugin.SetupClass2'
        assert p2['setup_class'] == setup_class2
        assert p2['my_arg'] == 'hello'
        assert p2['my_other_arg'] == 'world'
        assert p3['__name__'] == 'p3'
        setup_class3 = 'starcluster.tests.mytestplugin.SetupClass3'
        assert p3['setup_class'] == setup_class3
        assert p3['my_arg'] == 'bon'
        assert p3['my_other_arg'] == 'jour'
        assert p3['my_other_other_arg'] == 'monsignour'

    def test_plugin_not_defined(self):
        try:
            self.get_custom_config(**{'c1_plugs': 'p1,p2,p233'})
        except exception.ConfigError:
            pass
        else:
            raise Exception(
                'config allows non-existent plugins to be specified')

    def test_keypairs(self):
        kpairs = self.config.keys
        assert len(kpairs) == 3
        k1 = kpairs.get('k1')
        k2 = kpairs.get('k2')
        k3 = kpairs.get('k3')
        dcfg = tests.templates.config.default_config
        k1_location = os.path.expanduser(dcfg['k1_location'])
        k2_location = dcfg['k2_location']
        k3_location = dcfg['k3_location']
        assert k1 and k1['key_location'] == k1_location
        assert k2 and k2['key_location'] == k2_location
        assert k3 and k3['key_location'] == k3_location

    def test_keypair_not_defined(self):
        try:
            self.get_custom_config(**{'c1_keyname': 'k2323'})
        except exception.ConfigError:
            pass
        else:
            raise Exception(
                'config allows non-existent keypairs to be specified')

    def test_invalid_config(self):
        """
        Test that reading a non-INI formatted file raises an exception
        """
        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file.write(
            "<html>random garbage file with no section headings</html>")
        tmp_file.flush()
        try:
            config.StarClusterConfig(tmp_file.name, cache=True).load()
        except exception.ConfigHasNoSections:
            pass
        else:
            raise Exception("config allows non-INI formatted files")

    def test_empty_config(self):
        """
        Test that reading an empty config generates no errors and that aws
        credentials can be read from the environment.
        """
        aws_key = 'testkey'
        aws_secret_key = 'testsecret'
        os.environ['AWS_ACCESS_KEY_ID'] = aws_key
        os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
        tmp_file = tempfile.NamedTemporaryFile()
        cfg = config.StarClusterConfig(tmp_file.name, cache=True).load()
        assert cfg.aws['aws_access_key_id'] == aws_key
        assert cfg.aws['aws_secret_access_key'] == aws_secret_key

    def test_cyclical_extends(self):
        """
        Test that cyclical extends in the config raises an exception
        """
        try:
            self.get_custom_config(**{'c2_extends': 'c3',
                                      'c3_extends': 'c2'})
            self.get_custom_config(**{'c2_extends': 'c3',
                                      'c3_extends': 'c4',
                                      'c4_extends': 'c2'})
        except exception.ConfigError:
            pass
        else:
            raise Exception('config allows cyclical extends graph')

    def test_choices(self):
        """
        Test that config enforces a value to be one of a list of choices if
        specified
        """
        try:
            self.get_custom_config(**{'c1_shell': 'blahblah'})
        except exception.ConfigError:
            pass
        else:
            raise Exception('config not enforcing choices for setting')

    def test_multiple_instance_types(self):
        """
        Test that config properly handles multiple instance types syntax
        (within node_instance_type setting)
        """
        invalid_cases = [{'c1_node_type': 'c1.xlarge:ami-asdffdas'},
                 {'c1_node_type': 'c1.xlarge:3'},
                 {'c1_node_type': 'c1.xlarge:ami-asdffdas:3'},
                 {'c1_node_type': 'c1.xlarge:asdf:asdf:asdf,m1.small'},
                 {'c1_node_type': 'c1.asdf:4, m1.small'},
                 {'c1_node_type': 'c1.xlarge: 0, m1.small'},
                 {'c1_node_type': 'c1.xlarge:-1, m1.small'}]
        for case in invalid_cases:
            try:
                self.get_custom_config(**case)
            except exception.ConfigError:
                pass
            else:
                raise Exception(('config allows invalid multiple instance ' +
                                 'type syntax: %s') % case)
        valid_cases = [
            {'c1_node_type': 'c1.xlarge:3, m1.small'},
            {'c1_node_type': 'c1.xlarge:ami-asdfasdf:3, m1.small'},
            {'c1_node_type': 'c1.xlarge:ami-asdfasdf:3, m1.large, m1.small'},
            {'c1_node_type': 'm1.large, c1.xlarge:ami-asdfasdf:3, m1.large, ' +
             'm1.small'},
            {'c1_node_type': 'c1.xlarge:ami-asdfasdf:2, m1.large:2, m1.small'},
        ]
        for case in valid_cases:
            try:
                self.get_custom_config(**case)
            except exception.ConfigError:
                raise Exception(('config rejects valid multiple instance ' +
                                 'type syntax: %s') % case)
