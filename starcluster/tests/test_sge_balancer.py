import datetime

from starcluster.balancers import sge
from starcluster.tests import StarClusterTest
from starcluster.tests.templates import sge_balancer


class TestSGELoadBalancer(StarClusterTest):
    stat_hash = None
    host_hash = {}

    def test_qhost_parser(self):
        stat = sge.SGEStats()
        self.host_hash = stat.parse_qhost(sge_balancer.qhost_xml)
        assert len(self.host_hash) == 3
        assert len(self.host_hash) == stat.count_hosts()
        assert stat.count_total_slots() == 3
        assert stat.slots_per_host() == 1

    def test_loaded_qhost_parser(self):
        stat = sge.SGEStats()
        self.host_hash = stat.parse_qhost(sge_balancer.loaded_qhost_xml)
        assert len(self.host_hash) == 10
        assert len(self.host_hash) == stat.count_hosts()
        assert stat.count_total_slots() == 80
        assert stat.slots_per_host() == 8

    def test_qstat_parser(self):
        stat = sge.SGEStats()
        self.stat_hash = stat.parse_qstat(sge_balancer.qstat_xml)
        assert len(self.stat_hash) == 23
        assert stat.first_job_id == 1
        assert stat.last_job_id == 23
        assert len(stat.get_queued_jobs()) == 20
        assert len(stat.get_running_jobs()) == 3
        assert stat.num_slots_for_job(21) == 1
        oldest = datetime.datetime(2010, 6, 18, 23, 39, 14)
        assert stat.oldest_queued_job_age() == oldest

    def test_qacct_parser(self):
        stat = sge.SGEStats()
        now = datetime.datetime.utcnow()
        self.jobstats = stat.parse_qacct(sge_balancer.qacct_txt, now)
        assert stat.avg_job_duration() == 90
        assert stat.avg_wait_time() == 263

    def test_loaded_qstat_parser(self):
        stat = sge.SGEStats()
        self.stat_hash = stat.parse_qstat(sge_balancer.loaded_qstat_xml)
        assert len(self.stat_hash) == 192
        assert stat.first_job_id == 385
        assert stat.last_job_id == 576
        assert len(stat.get_queued_jobs()) == 188
        assert len(stat.get_running_jobs()) == 4
        assert stat.num_slots_for_job(576) == 20
        oldest = datetime.datetime(2010, 7, 8, 4, 40, 32)
        assert stat.oldest_queued_job_age() == oldest

    def test_node_working(self):
        #TODO : FINISH THIS
        pass
