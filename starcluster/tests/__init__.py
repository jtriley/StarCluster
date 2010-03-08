import unittest
import tempfile
from starcluster.config import StarClusterConfig
from starcluster.tests.templates.config import config_test_template, default_config

class StarClusterTest(unittest.TestCase):

    __cfg = None

    @property
    def config(self):
        """ Returns (valid) default test config """
        if not self.__cfg:
            tmp_file = tempfile.NamedTemporaryFile()
            tmp_file.write(config_test_template % default_config)
            tmp_file.flush()
            self.__cfg = StarClusterConfig(tmp_file.name, cache=True); self.__cfg.load()
        return self.__cfg

    def get_custom_config(self, **kwargs):
        """ Returns default test config modified by kwargs """
        tmp_file = tempfile.NamedTemporaryFile()
        kwords = {}; 
        kwords.update(default_config)
        kwords.update(kwargs)
        tmp_file.write(config_test_template % kwords);
        tmp_file.flush()
        cfg = StarClusterConfig(tmp_file.name, cache=True); cfg.load()
        return cfg
