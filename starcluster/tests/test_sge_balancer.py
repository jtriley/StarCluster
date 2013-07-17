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

import datetime

from starcluster.balancers import sge
from starcluster.tests import StarClusterTest
from starcluster.tests.templates import sge_balancer


class TestSGELoadBalancer(StarClusterTest):

    def test_qhost_parser(self):
        stat = sge.SGEStats()
        host_hash = stat.parse_qhost(sge_balancer.qhost_xml)
        assert len(host_hash) == 3
        assert len(host_hash) == stat.count_hosts()

    def test_loaded_qhost_parser(self):
        stat = sge.SGEStats()
        host_hash = stat.parse_qhost(sge_balancer.loaded_qhost_xml)
        assert len(host_hash) == 10
        assert len(host_hash) == stat.count_hosts()

    def test_qstat_parser(self):
        stat = sge.SGEStats()
        stat_hash = stat.parse_qstat(sge_balancer.qstat_xml)
        assert len(stat_hash) == 23
        assert stat.first_job_id == 1
        assert stat.last_job_id == 23
        assert len(stat.get_queued_jobs()) == 20
        assert len(stat.get_running_jobs()) == 3
        assert stat.num_slots_for_job(21) == 1
        oldest = datetime.datetime(2010, 6, 18, 23, 39, 14)
        assert stat.oldest_queued_job_age() == oldest
        assert len(stat.queues) == 3

    def test_qacct_parser(self):
        stat = sge.SGEStats()
        now = datetime.datetime.utcnow()
        self.jobstats = stat.parse_qacct(sge_balancer.qacct_txt, now)
        assert stat.avg_job_duration() == 90
        assert stat.avg_wait_time() == 263

    def test_loaded_qstat_parser(self):
        stat = sge.SGEStats()
        stat_hash = stat.parse_qstat(sge_balancer.loaded_qstat_xml)
        assert len(stat_hash) == 192
        assert stat.first_job_id == 385
        assert stat.last_job_id == 576
        assert len(stat.get_queued_jobs()) == 188
        assert len(stat.get_running_jobs()) == 4
        assert stat.num_slots_for_job(576) == 20
        oldest = datetime.datetime(2010, 7, 8, 4, 40, 32)
        assert stat.oldest_queued_job_age() == oldest
        assert len(stat.queues) == 10
        assert stat.count_total_slots() == 80
        stat.parse_qhost(sge_balancer.loaded_qhost_xml)
        assert stat.slots_per_host() == 8

    def test_node_working(self):
        #TODO : FINISH THIS
        pass
