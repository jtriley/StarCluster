#!/usr/bin/env python

import datetime

from starcluster import tests
from starcluster.tests import StarClusterTest
from starcluster.tests import templates
from starcluster.balancers import sge


class TestSGELoadBalancer(StarClusterTest):
    hostHash = {}

    def test_qhost_parser(self):
        stat = sge.SGEStats()
        self.hostHash = stat.parse_qhost(tests.templates.sge.qhost_xml)
        assert len(self.hostHash) == 3
        assert len(self.hostHash) == stat.count_hosts()
        assert stat.count_total_slots() == 3
        assert stat.slots_per_host() == 1
        print "QHOST TEST PASSED"

    def test_loaded_qhost_parser(self):
        stat = sge.SGEStats()
        self.hostHash = stat.parse_qhost(templates.sge.loaded_qhost_xml)
        assert len(self.hostHash) == 10
        assert len(self.hostHash) == stat.count_hosts()
        assert stat.count_total_slots() == 80
        assert stat.slots_per_host() == 8
        print "LOADED QHOST TEST PASSED"

    def test_qstat_parser(self):
        stat = sge.SGEStats()
        self.statHash = stat.parse_qstat(tests.templates.sge.qstat_xml)
        assert len(self.statHash) == 23
        assert stat.first_job_id == 1
        assert stat.last_job_id == 23
        assert len(stat.get_queued_jobs()) == 20
        assert len(stat.get_running_jobs()) == 3
        assert stat.num_slots_for_job(21) == 1
        oldest = datetime.datetime(2010, 6, 18, 23, 39, 14)
        assert stat.oldest_queued_job_age() == oldest
        print "QSTAT TEST PASSED"

    def test_qacct_parser(self):
        stat = sge.SGEStats()
        now = datetime.datetime.utcnow()
        self.jobstats = stat.parse_qacct(tests.templates.sge.qacct_txt, now)
        assert stat.avg_job_duration() == 90
        assert stat.avg_wait_time() == 263
        print "QACCT TEST PASSED"

    def test_loaded_qstat_parser(self):
        stat = sge.SGEStats()
        self.statHash = stat.parse_qstat(tests.templates.sge.loaded_qstat_xml)
        assert len(self.statHash) == 192
        assert stat.first_job_id == 385
        assert stat.last_job_id == 576
        assert len(stat.get_queued_jobs()) == 188
        assert len(stat.get_running_jobs()) == 4
        assert stat.num_slots_for_job(576) == 20
        oldest = datetime.datetime(2010, 7, 8, 4, 40, 32)
        assert stat.oldest_queued_job_age() == oldest
        print "LOADED QSTAT TEST PASSED"

    def test_node_working(self):
        #TODO : FINISH THIS
        pass

    def runTest(self):
        print "Testing with normal files."
        self.test_qhost_parser()
        self.test_qstat_parser()
        self.test_qacct_parser()

        print "Testing with large files."
        self.test_loaded_qhost_parser()
        self.test_loaded_qstat_parser()
