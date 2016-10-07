# Copyright 2009-2014 Justin Riley
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

"""
ThreadPool module for StarCluster based on WorkerPool
"""
import time
import Queue
import thread
import traceback
import workerpool

from starcluster import exception
from starcluster import progressbar
from starcluster.logger import log


class DaemonWorker(workerpool.workers.Worker):
    """
    Improved Worker that sets daemon = True by default and also handles
    communicating exceptions to the parent pool object by adding them to
    the parent pool's exception queue
    """
    def __init__(self, *args, **kwargs):
        super(DaemonWorker, self).__init__(*args, **kwargs)
        self.daemon = True

    def run(self):
        "Get jobs from the queue and perform them as they arrive."
        while 1:
            # Sleep until there is a job to perform.
            job = self.jobs.get()
            try:
                job.run()
            except workerpool.exceptions.TerminationNotice:
                break
            except Exception, e:
                tb_msg = traceback.format_exc()
                jid = job.jobid or str(thread.get_ident())
                self.jobs.store_exception([e, tb_msg, jid])
            finally:
                self.jobs.task_done()


def _worker_factory(parent):
    return DaemonWorker(parent)


class SimpleJob(workerpool.jobs.SimpleJob):
    def __init__(self, method, args=[], kwargs={}, jobid=None,
                 results_queue=None):
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.jobid = jobid
        self.results_queue = results_queue

    def run(self):
        if isinstance(self.args, list) or isinstance(self.args, tuple):
            if isinstance(self.kwargs, dict):
                r = self.method(*self.args, **self.kwargs)
            else:
                r = self.method(*self.args)
        elif self.args is not None and self.args is not []:
            if isinstance(self.kwargs, dict):
                r = self.method(self.args, **self.kwargs)
            else:
                r = self.method(self.args)
        else:
            r = self.method()
        if self.results_queue:
            return self.results_queue.put(r)
        return r


class ThreadPool(workerpool.WorkerPool):
    def __init__(self, size=1, maxjobs=0, worker_factory=_worker_factory,
                 disable_threads=False):
        self.disable_threads = disable_threads
        self._exception_queue = Queue.Queue()
        self._results_queue = Queue.Queue()
        self._progress_bar = None
        if self.disable_threads:
            size = 0
        workerpool.WorkerPool.__init__(self, size, maxjobs, worker_factory)

    @property
    def progress_bar(self):
        if not self._progress_bar:
            widgets = ['', progressbar.Fraction(), ' ',
                       progressbar.Bar(marker=progressbar.RotatingMarker()),
                       ' ', progressbar.Percentage(), ' ', ' ']
            pbar = progressbar.ProgressBar(widgets=widgets, maxval=1,
                                           force_update=True)
            self._progress_bar = pbar
        return self._progress_bar

    def simple_job(self, method, args=[], kwargs={}, jobid=None,
                   results_queue=None):
        results_queue = results_queue or self._results_queue
        job = SimpleJob(method, args, kwargs, jobid,
                        results_queue=results_queue)
        if not self.disable_threads:
            return self.put(job)
        else:
            return job.run()

    def get_results(self):
        results = []
        for i in range(self._results_queue.qsize()):
            results.append(self._results_queue.get())
        return results

    def map(self, fn, *seq, **kwargs):
        """
        Uses the threadpool to return a list of the results of applying the
        function to the items of the argument sequence(s). If more than one
        sequence is given, the function is called with an argument list
        consisting of the corresponding item of each sequence. If more than one
        sequence is given with different lengths the argument list will be
        truncated to the length of the smallest sequence.

        If the kwarg jobid_fn is specified then each threadpool job will be
        assigned a jobid based on the return value of jobid_fn(item) for each
        item in the map.
        """
        if self._results_queue.qsize() > 0:
            self.get_results()
        args = zip(*seq)
        jobid_fn = kwargs.get('jobid_fn')
        for seq in args:
            jobid = None
            if jobid_fn:
                jobid = jobid_fn(*seq)
            self.simple_job(fn, seq, jobid=jobid)
        return self.wait(numtasks=len(args))

    def store_exception(self, e):
        self._exception_queue.put(e)

    def shutdown(self):
        log.info("Shutting down threads...")
        workerpool.WorkerPool.shutdown(self)
        self.wait(numtasks=self.size())

    def wait(self, numtasks=None, return_results=True):
        pbar = self.progress_bar.reset()
        pbar.maxval = self.unfinished_tasks
        if numtasks is not None:
            pbar.maxval = max(numtasks, self.unfinished_tasks)
        while self.unfinished_tasks != 0:
            finished = pbar.maxval - self.unfinished_tasks
            pbar.update(finished)
            log.debug("unfinished_tasks = %d" % self.unfinished_tasks)
            time.sleep(1)
        if pbar.maxval != 0:
            pbar.finish()
        self.join()
        exc_queue = self._exception_queue
        if exc_queue.qsize() > 0:
            excs = [exc_queue.get() for i in range(exc_queue.qsize())]
            raise exception.ThreadPoolException(
                "An error occurred in ThreadPool", excs)
        if return_results:
            return self.get_results()

    def __del__(self):
        log.debug('del called in threadpool')
        self.shutdown()
        self.join()


def get_thread_pool(size=10, worker_factory=_worker_factory,
                    disable_threads=False):
    return ThreadPool(size=size, worker_factory=_worker_factory,
                      disable_threads=disable_threads)
