# Copyright 2014 Mich
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

import logging
logging.disable(logging.WARN)

from starcluster import tests
from starcluster.node import Node
from starcluster.cluster import Cluster


class FooNode(Node):
    def __init__(self, alias, private_ip_address):
        self._alias = alias
        self._private_ip_address = private_ip_address

    @property
    def private_ip_address(self):
        return self._private_ip_address


class TestStarClusterGeneric(tests.StarClusterTest):

    def test_filter_etc_hosts_lines(self):
        n = FooNode("node001.starcluster.com", "1.2.3.4")
        lines = ["1.2.3.44 master",
                 "1.2.3.4\tnode002",
                 "1.2.3.9 node001",
                 "1.2.3.444 node003",
                 "3.4.5.6 node004",
                 "11.2.3.4 node005"]
        kept, rejected = Node.filter_etc_hosts_lines([n], lines)
        assert len(kept) == 4
        assert kept[0] == lines[0]
        assert kept[1] == lines[3]
        assert kept[2] == lines[4]
        assert kept[3] == lines[5]
        assert len(rejected) == 2
        assert rejected[0] == lines[1]
        assert rejected[1] == lines[2]

    def test_get_free_node_nums(self):
        res = Cluster.get_free_ids_among_nodes(0, [])
        assert res == []

        node001 = FooNode("node001", "1.2.3.4")
        res = Cluster.get_free_ids_among_nodes(1, [node001])
        assert res == [2]

        res = Cluster.get_free_ids_among_nodes(3, [node001])
        assert res == [2, 3, 4]

        node003 = FooNode("node003", "1.2.3.4")
        node005 = FooNode("node005", "1.2.3.4")
        node006 = FooNode("node006", "1.2.3.4")
        node106 = FooNode("node106", "1.2.3.4")
        res = Cluster.get_free_ids_among_nodes(5, [node001, node003, node005,
                                                   node006, node106])
        assert res == [2, 4, 7, 8, 9]
