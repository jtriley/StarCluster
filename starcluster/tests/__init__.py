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
