import os
import tempfile

import logging
logging.disable(logging.WARN)

from starcluster.logger import log
from starcluster import exception
from starcluster.tests import StarClusterTest
from starcluster.static import STARCLUSTER_CFG_FILE
from starcluster.config import StarClusterConfig
from starcluster.tests.templates.config import default_config, config_test_template

class TestStarClusterConfig(StarClusterTest):

    def test_valid_config_template(self):
        cfg = self.config

    def test_config_dne(self):
        tmp_file = tempfile.NamedTemporaryFile()
        non_existent_file = tmp_file.name
        tmp_file.close()
        assert not os.path.exists(non_existent_file)
        try:
            cfg = StarClusterConfig(non_existent_file, cache=True); cfg.load()
        except exception.ConfigNotFound,e:
            pass
        else:
            raise Exception('config loaded non-existent config file %s' % path)

    def test_get_cluster(self):
        cluster = self.config.get_cluster_template('c1')
        try:
            self.config.get_cluster_template('no_such_cluster')
        except exception.ClusterTemplateDoesNotExist,e:
            pass
        else:
            raise Exception('config returned non-existent cluster')

    def test_int_required(self):
        cases = [{'c1_size':'-s'}, {'c1_size': 2.5}, {'v1_partition': 'asdf'},
                 {'v1_partition': 0.33}]
        for case in cases:
            try:
                cfg = self.get_custom_config(**case)
            except exception.ConfigError,e:
                pass
            else:
                raise Exception('config is not enforcing ints correctly')

    def test_missing_required(self):
        pass

    def test_volumes(self):
        c1 = self.config.get_cluster_template('c1')
        vols = c1.volumes
        assert len(vols) == 3
        assert vols.has_key('v1')
        v1 = vols['v1']
        assert v1.has_key('volume_id') and v1['volume_id'] == 'vol-c999999'
        assert v1.has_key('device') and v1['device'] == '/dev/sdj'
        assert v1.has_key('partition') and v1['partition'] == '/dev/sdj1'
        assert v1.has_key('mount_path') and v1['mount_path'] == '/volume1'
        assert vols.has_key('v2')
        v2 = vols['v2']
        assert v2.has_key('volume_id') and v2['volume_id'] == 'vol-c888888'
        assert v2.has_key('device') and v2['device'] == '/dev/sdk'
        assert v2.has_key('partition') and v2['partition'] == '/dev/sdk1'
        assert v2.has_key('mount_path') and v2['mount_path'] == '/volume2'
        assert vols.has_key('v3')
        v3 = vols['v3']
        assert v3.has_key('volume_id') and v3['volume_id'] == 'vol-c777777'
        assert v3.has_key('device') and v3['device'] == '/dev/sdl'
        assert v3.has_key('partition') and v3['partition'] == '/dev/sdl1'
        assert v3.has_key('mount_path') and v3['mount_path'] == '/volume3'

    def test_volume_not_defined(self):
        try:
            cfg = self.get_custom_config(**{'c1_vols': 'v1,v2,v2323'})
        except exception.ConfigError,e:
            pass
        else:
            raise Exception('config allows non-existent volumes to be specified')

    def test_clusters(self):
        assert self.config.clusters.has_key('c1')
        assert self.config.clusters.has_key('c2')
        assert self.config.clusters.has_key('c3')

    def test_extends(self):
        c1 = self.config.clusters.get('c1')
        c2 = self.config.clusters.get('c2')
        c3 = self.config.clusters.get('c3')
        c2_settings = ['__name__', 'extends', 'keyname', 'key_location', 'cluster_size', 'node_instance_type',
                       'master_instance_type', 'volumes']
        c3_settings = ['__name__', 'extends', 'keyname', 'key_location', 'cluster_size', 'volumes']
        for key in c1:
            if c2.has_key(key) and not key in c2_settings:
                assert c2[key] == c1[key]
            else:
                # below only true for default test config, not required in general
                assert c2[key] != c1[key]
        for key in c2:
            if c3.has_key(key) and not key in c3_settings:
                assert c3[key] == c2[key]
            else:
                # below only true for default test config, not required in general
                assert c3[key] != c2[key]

    def test_plugins(self):
        c1 = self.config.get_cluster_template('c1')
        plugs = c1.plugins
        assert len(plugs) == 3
        # test that order is preserved 
        p1 = plugs[0]
        p2 = plugs[1]
        p3 = plugs[2]
        assert p1['__name__'] == 'p1'
        assert p1['setup_class'] == 'starcluster.tests.mytestplugin.SetupClass'
        assert p1['my_arg'] == '23'
        assert p1['my_other_arg'] == 'skidoo'
        assert p2['__name__'] == 'p2'
        assert p2['setup_class'] == 'starcluster.tests.mytestplugin.SetupClass2'
        assert p2['my_arg'] == 'hello'
        assert p2['my_other_arg'] == 'world'
        assert p3['__name__'] == 'p3'
        assert p3['setup_class'] == 'starcluster.tests.mytestplugin.SetupClass3'
        assert p3['my_arg'] == 'bon'
        assert p3['my_other_arg'] == 'jour'
        assert p3['my_other_other_arg'] == 'monsignour'

    def test_plugin_not_defined(self):
        try:
            cfg = self.get_custom_config(**{'c1_plugs': 'p1,p2,p233'})
        except exception.ConfigError,e:
            pass
        else:
            raise Exception('config allows non-existent plugins to be specified')

    def test_keypairs(self):
        kpairs = self.config.keys
        assert len(kpairs) == 3
        k1 = kpairs.get('k1')
        k2 = kpairs.get('k2')
        k3 = kpairs.get('k3')
        assert k1 and k1['key_location'] == '/path/to/k1_rsa'
        assert k2 and k2['key_location'] == '/path/to/k2_rsa'
        assert k3 and k3['key_location'] == '/path/to/k3_rsa'

    def test_keypair_not_defined(self):
        try:
            cfg = self.get_custom_config(**{'c1_keyname': 'k2323'})
        except exception.ConfigError,e:
            pass
        else:
            raise Exception('config allows non-existent keypairs to be specified')

    def test_invalid_config(self):
        """
        Test that reading a non-INI formatted file raises an exception
        """
        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file.write("""<html>random garbage file with no section headings</html>""")
        tmp_file.flush()
        try:
            cfg = StarClusterConfig(tmp_file.name, cache=True); cfg.load()
        except exception.ConfigHasNoSections,e:
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
        cfg = StarClusterConfig(tmp_file.name, cache=True); cfg.load()
        assert cfg.aws['aws_access_key_id'] == aws_key
        assert cfg.aws['aws_secret_access_key'] == aws_secret_key
