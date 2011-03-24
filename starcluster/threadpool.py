#!/usr/bin/env python
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
                pass
            except Exception, e:
                tb_msg = traceback.format_exc()
                jid = job.jobid or str(thread.get_ident())
                self.jobs.store_exception([e, tb_msg, jid])
            finally:
                self.jobs.task_done()


def _worker_factory(parent):
    return DaemonWorker(parent)


class SimpleJob(workerpool.jobs.SimpleJob):
    def __init__(self, method, args=[], jobid=None):
        self.method = method
        self.args = args
        self.jobid = jobid

    def run(self):
        if isinstance(self.args, list) or isinstance(self.args, tuple):
            r = self.method(*self.args)
        elif isinstance(self.args, dict):
            r = self.method(**self.args)
        else:
            r = self.method(self.args)
        return r


class ThreadPool(workerpool.WorkerPool):
    def __init__(self, size=1, maxjobs=0, worker_factory=_worker_factory,
                 disable_threads=False):
        self.disable_threads = disable_threads
        self._exception_queue = Queue.Queue()
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
            pbar = progressbar.ProgressBar(widgets=widgets,
                                           maxval=1,
                                           force_update=True)
            self._progress_bar = pbar
        return self._progress_bar

    def simple_job(self, method, args=[], jobid=None):
        job = SimpleJob(method, args, jobid)
        if not self.disable_threads:
            return self.put(job)
        else:
            return job.run()

    def store_exception(self, e):
        self._exception_queue.put(e)

    def wait(self):
        pbar = self.progress_bar.reset()
        pbar.maxval = self.unfinished_tasks
        while self.unfinished_tasks != 0:
            finished = pbar.maxval - self.unfinished_tasks
            pbar.update(finished)
            log.debug("unfinished_tasks = %d" % self.unfinished_tasks)
            time.sleep(1)
        if pbar.maxval != 0:
            pbar.finish()
        self.join()
        if self._exception_queue.qsize() > 0:
            raise exception.ThreadPoolException(
                "An error occured in ThreadPool", self._exception_queue.queue)

    def __del__(self):
        log.debug('del called in threadpool')
        self.shutdown()
        self.join()

def get_thread_pool(size=10, worker_factory=_worker_factory,
                    disable_threads=False):
    return ThreadPool(size=size, worker_factory=_worker_factory,
                      disable_threads=disable_threads)
