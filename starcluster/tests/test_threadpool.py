import logging
import tempfile
logging.disable(logging.WARN)

from starcluster import tests
from starcluster import exception
from starcluster import threadpool


class TestThreadPool(tests.StarClusterTest):

    _jobs = 5
    _mykw = 'StarCluster!!!'
    _pool = None

    @property
    def pool(self):
        if not self._pool:
            self._pool = threadpool.get_thread_pool(10, disable_threads=False)
            fd = tempfile.TemporaryFile()
            self._pool.progress_bar.fd = fd
        return self._pool

    def _no_args(self):
        pass

    def _args_only(self, i):
        return i

    def _kwargs_only(self, mykw=None):
        return mykw

    def _args_and_kwargs(self, i, mykw=None):
        return (i, dict(mykw=mykw))

    def test_no_args(self):
        pool = self.pool
        try:
            for i in range(self._jobs):
                pool.simple_job(self._no_args, jobid=i)
            results = pool.wait(numtasks=self._jobs)
            print "no_args: %s" % results
            assert results.count(None) == self._jobs
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())

    def test_args_only(self):
        try:
            pool = self.pool
            for i in range(self._jobs):
                pool.simple_job(self._args_only, i, jobid=i)
            results = pool.wait(numtasks=self._jobs)
            results.sort()
            print "args_only: %s" % results
            assert results == range(self._jobs)
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())

    def test_kwargs_only(self):
        pool = self.pool
        try:
            for i in range(self._jobs):
                pool.simple_job(self._kwargs_only,
                                kwargs=dict(mykw=self._mykw), jobid=i)
            results = pool.wait(numtasks=self._jobs)
            print "kwargs_only: %s" % results
            assert results.count(self._mykw) == self._jobs
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())

    def test_args_and_kwargs(self):
        pool = self.pool
        try:
            for i in range(self._jobs):
                pool.simple_job(self._args_and_kwargs, i,
                                kwargs=dict(mykw=self._mykw), jobid=i)
            results = pool.wait(numtasks=self._jobs)
            results.sort()
            print "args_and_kwargs: %s" % results
            assert results == zip(range(self._jobs),
                                  [dict(mykw=self._mykw)] * self._jobs)
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())

    def test_threadpool_map(self):
        try:
            r = 20
            ref = map(lambda x: x ** 2, range(r))
            calc = self.pool.map(lambda x: x ** 2, range(r))
            calc.sort()
            assert ref == calc
            for i in range(r):
                self.pool.simple_job(lambda x: x ** 2, i, jobid=i)
            self.pool.wait(return_results=False)
            calc = self.pool.map(lambda x: x ** 2, range(r))
            calc.sort()
            assert ref == calc
        except exception.ThreadPoolException, e:
            raise Exception(e.format_excs())
