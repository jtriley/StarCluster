import unittest
import tempfile

from starcluster.config import StarClusterConfig
from starcluster.tests.templates import config


class StarClusterTest(unittest.TestCase):

    __cfg = None

    @property
    def config(self):
        """ Returns (valid) default test config """
        if not self.__cfg:
            tmp_file = tempfile.NamedTemporaryFile()
            tmp_file.write(config.config_test_template % config.default_config)
            tmp_file.flush()
            self.__cfg = StarClusterConfig(tmp_file.name, cache=True).load()
        return self.__cfg

    def get_config(self, contents, cache=False):
        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file.write(contents)
        tmp_file.flush()
        cfg = StarClusterConfig(tmp_file.name, cache=cache).load()
        return cfg

    def get_custom_config(self, **kwargs):
        """ Returns default test config modified by kwargs """
        kwords = {}
        kwords.update(config.default_config)
        kwords.update(kwargs)
        cfg = self.get_config(config.config_test_template % kwords)
        return cfg
