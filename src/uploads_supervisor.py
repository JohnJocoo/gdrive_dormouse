from files_upload_job import FeedbackCommand as Command
from files_upload_job import FilesUploadJob
from typing import List, Callable
from pydrive.drive import GoogleDrive
from queue import Queue
from threading import Thread
from concurrent.futures import Future


PathExceptions = List[str]
Path = str
Seconds = int
GDriveFactory = Callable[[], GoogleDrive]


class Events:
    scan_jobs           = 'scan_jobs'
    add_job             = 'add_job'
    stop_all            = 'stop_all'
    get_progress        = 'get_progress'
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
        self._events_queue      = Queue()
        self._thread            = Thread(name='UploadsSupervisor', 
                                         target=self._run)

    def start(self):
        self._thread.start()
        self._events_queue.put((Events.scan_jobs, None), timeout=5)
        
    def stop(self):
        self._events_queue.put((Events.stop_all, None), timeout=5)
        self._thread.join(timeout=150.0)
        
    def add_job(self, job: str):
        self._events_queue.put((Events.add_job, job), timeout=5)
        
    def get_progress(self):
        future = Future()
        self._events_queue.put((Events.get_progress, future), timeout=5)
        return future.result(timeout=5)
        
    def _rescan(self):
        self._events_queue.put((Events.scan_jobs, None), timeout=5)
        
    
