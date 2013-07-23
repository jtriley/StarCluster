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

from starcluster.logger import log
from starcluster.clustersetup import ClusterSetup


class SetupClass(ClusterSetup):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __init__(self, my_arg, my_other_arg):
        self.my_arg = my_arg
        self.my_other_arg = my_other_arg
        log.debug(
            "setupclass: my_arg = %s, my_other_arg = %s" % (my_arg,
                                                            my_other_arg))

    def run(self, nodes, master, user, shell, volumes):
        log.debug('Hello from MYPLUGIN :D')
        for node in nodes:
            node.ssh.execute('apt-get install -y imagemagick')
            node.ssh.execute('echo "i ran foo" >> /tmp/iran')


class SetupClass2(ClusterSetup):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __init__(self, my_arg, my_other_arg):
        self.my_arg = my_arg
        self.my_other_arg = my_other_arg
        log.debug("setupclass2: my_arg = %s, my_other_arg = %s" %
                  (my_arg, my_other_arg))

    def run(self, nodes, master, user, shell, volumes):
        log.debug('Hello from MYPLUGIN2 :D')
        for node in nodes:
            node.ssh.execute('apt-get install -y python-utidylib')
            node.ssh.execute('echo "i ran too foo" >> /tmp/iran')


class SetupClass3(ClusterSetup):
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __init__(self, my_arg, my_other_arg, my_other_other_arg):
        self.my_arg = my_arg
        self.my_other_arg = my_other_arg
        self.my_other_other_arg = my_other_other_arg
        msg = "setupclass3: my_arg = %s, my_other_arg = %s"
        msg += " my_other_other_arg = %s"
        log.debug(msg % (my_arg, my_other_arg, my_other_other_arg))

    def run(self, nodes, master, user, shell, volumes):
        log.debug('Hello from MYPLUGIN3 :D')
        for node in nodes:
            node.ssh.execute('apt-get install -y python-boto')
            node.ssh.execute('echo "i ran also foo" >> /tmp/iran')
