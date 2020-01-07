from files_upload_job import FeedbackCommand as Command
from files_upload_job import FilesUploadJob
from typing import List, Callable, Tuple
from pydrive.drive import GoogleDrive
from queue import Queue
from threading import Thread, Timer
from concurrent.futures import Future
import logging
from os.path import join as fs_join
from functools import reduce
import os


PathExceptions = List[str]
Path = str
Seconds = int
GDriveFactory = Callable[[], GoogleDrive]


class Events:
    scan_jobs           = 'scan_jobs'
    add_job             = 'add_job'
    stop_all            = 'stop_all'
    get_progress        = 'get_progress'
    get_jobs_n          = 'get_jobs_n'
    retry_job           = 'retry_job'
    schedule_retry_job  = Command.schedule_retry
    release_job         = Command.release
    job_terminated      = Command.terminated


class UploadsSupervisor:
    
    def __init__(self, gdrive_factory: GDriveFactory, 
                 jobs_path: Path, drive_dst_path: str,
                 file_exceptions: PathExceptions = []):
        self._gdrive_factory    = gdrive_factory
        self._jobs_path         = jobs_path
        self._drive_dst_path    = drive_dst_path
        self._file_exceptions   = file_exceptions
        self._jobs              = {}
        self._scheduled_jobs    = {}
        self._scheduled_timers  = {}
        self._events_queue      = Queue()
        self._log               = logging.getLogger('UploadsSupervisor')
        self._thread            = Thread(name='UploadsSupervisor', 
                                         target=self._run)
                                         
        self._event_handlers    = {
            Events.scan_jobs            : self._scan_jobs_impl,
            Events.add_job              : self._add_job_impl,
            Events.stop_all             : self._stop_all_impl,
            Events.get_progress         : self._get_progress_impl,
            Events.retry_job            : self._retry_job_impl,
            Events.schedule_retry_job   : self._schedule_retry_job_impl,
            Events.release_job          : self._release_job_impl,
            Events.job_terminated       : self._job_terminated_impl,
            Events.get_jobs_n           : self._get_jobs_n_impl}

    def start(self):
        self._thread.start()
        self._events_queue.put((Events.scan_jobs, None), timeout=5)
        
    def stop(self):
        self._events_queue.put((Events.stop_all, None), timeout=5)
        self._thread.join(timeout=150.0)
        
    def add_job(self, job: str):
        self._events_queue.put((Events.add_job, job), timeout=5)
        
    # -> (files_process, size_process)
    def get_progress(self) -> Tuple[float, float]:
        future = Future()
        self._events_queue.put((Events.get_progress, future), timeout=5)
        return future.result(timeout=5)
        
    def get_jobs_number(self) -> int:
        future = Future()
        self._events_queue.put((Events.get_jobs_n, future), timeout=5)
        return future.result(timeout=5)
        
    def _rescan(self):
        self._events_queue.put((Events.scan_jobs, None), timeout=5)
    
    def _scan_jobs_impl(self, _1, _2):
        entries = os.scandir(self._jobs_path)
        dirs = [f for f in entries if f.is_dir(follow_symlinks=True)]
        for dir_entry in dirs:
            if self._has_job(dir_entry.name):
                continue
            self.add_job(dir_entry.name)
        
    def _add_job_impl(self, _, job_name):
        self._log.info('trying to add new Job "%s"', str(job_name))
        self._create_job(job_name)
        
    def _retry_job_impl(self, _, job_name):
        if job_name not in self._scheduled_jobs:
            self._log.error('Job "%s" cannot be retried, no data', str(job_name))
            return
        retry_state = self._scheduled_jobs[job_name]
        del self._scheduled_jobs[job_name]
        if job_name in self._scheduled_timers:
            del self._scheduled_timers[job_name]
        self._log.info('retrying Job "%s"', str(job_name))
        self._create_job(job_name, retry_state)
        
    def _create_job(self, job_name, retry_state=None):
        if self._has_job(job_name):
            self._log.warning('Job "%s" already exists', str(job_name))
            return
        
        def job_callback(event, data):
            self._events_queue.put((event, (job_name, data)), timeout=5)
        
        job = FilesUploadJob(drive=self._gdrive_factory(), 
                             job_id=job_name,
                             local_src_path=fs_join(self._jobs_path, job_name), 
                             drive_dst_path=self._drive_dst_path,
                             feedback_callback=job_callback,
                             file_exceptions=self._file_exceptions)
        self._jobs[job_name] = job
        if retry_state is None:
            job.start()
        else:
            job.start(retry_state)
        self._log.info('Job "%s" created', str(job_name))
        
    def _stop_all_impl(self, _1, _2):
        self._log.info('stopping all')
        self._scheduled_jobs = {}
        for _, timer in self._scheduled_timers.items():
            timer.cancel()
        self._scheduled_timers = {}
        for _, job in self._jobs.items():
            job.stop()
        self._jobs = {}
        
    def _get_jobs_n_impl(self, _, promise):
        promise.set_result(len(self._jobs))
        
    def _get_progress_impl(self, _, promise):
        try:
            promise.set_result(self._rep_progress_impl())
        except Exception as e:
            promise.set_exception(e)
        
    def _rep_progress_impl(self):
        if len(self._jobs) == 0:
            return 0.0, 0.0
            
        def div_ign(val, denom):
            if int(denom) == 0:
                return 0.0
            return val/denom
            
        # ((progress_files, progress_size), (total_files, total_size))
        progress_totals = [(job.progress, job.total) 
                           for _, job in self._jobs.items()]
        progresses, totals = map(list, zip(*progress_totals))
        progress_files, progress_size = map(list, zip(*progresses))
        total_files_l, total_size_l = map(list, zip(*totals))
        total_files = reduce(lambda x, y: x + y, total_files_l, 0.0)
        total_size = reduce(lambda x, y: x + y, total_size_l, 0.0)
        files_mul = [div_ign(float(val), total_files) for val in total_files_l]
        size_mul = [div_ign(float(val), total_size) for val in total_size_l]
        progress_files_adj = [val*mul for val, mul in 
                              list(zip(progress_files, files_mul))]
        progress_size_adj = [val*mul for val, mul in 
                             list(zip(progress_size, size_mul))]
        res_files = reduce(lambda x, y: x + y, progress_files_adj, 0.0)
        res_size = reduce(lambda x, y: x + y, progress_size_adj, 0.0)
        return res_files, res_size
        
    def _schedule_retry_job_impl(self, _, data):
        job_name, sched_data = data
        self._log.info('scheduling retry for Job "%s"', str(job_name))
        seconds, state = sched_data
        
        def retry_job():
            self._events_queue.put((Events.retry_job, job_name), timeout=5)
        
        self._scheduled_jobs[job_name] = state
        timer = Timer(float(seconds), retry_job)
        self._scheduled_timers[job_name] = timer
        timer.start()
        
    def _release_job_impl(self, _, data):
        job_name, _ = data
        self._log.info('releasing Job "%s"', str(job_name))
        if job_name in self._jobs:
            del self._jobs[job_name]
        
    def _job_terminated_impl(self, _, data):
        job_name, _ = data
        self._log.error('Job "%s" terminated', str(job_name))
        if job_name in self._jobs:
            del self._jobs[job_name]
        self._schedule_retry_job_impl(Events.schedule_retry_job, 
                                      (job_name, (30 * 60, None)))
        
    def _has_job(self, job_name):
        in_jobs = job_name in self._jobs
        in_scheduled = job_name in self._scheduled_jobs
        return in_jobs or in_scheduled
    
    def _run(self):
        self._log.info('UploadsSupervisor started')
        while True:
            event = None
            try:
                event, data = self._events_queue.get()
                self._process_event(event, data)
            except Exception as e:
                self._log.error('error during event processing %s', str(e))
            if event == Events.stop_all:
                break
        self._log.info('UploadsSupervisor finished')
        
    def _process_event(self, event, data):
        self._log.info('processing event %s with data <%s>', str(event), str(data))
        if event not in self._event_handlers:
            self._log.error('unknown event %s', str(event))
            return
        self._event_handlers[event](event, data)
