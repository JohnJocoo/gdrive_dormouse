from typing import Callable, Any, List, Union
from files_upload_sm import Command, FilesUploadSM
from files_upload_sm import Path, Seconds, State
from files_upload_sm import Lock, Session, CommandT
from files_upload_sm import ScheduleData, UploadData
from files_upload_sm import CommandData, SideEffect, SideEffects
from pydrive.drive import GoogleDrive
from pydrive.auth import RefreshError
from pydrive.files import ApiRequestError
from threading import Thread
import os
import fcntl
import shutil
from functools import reduce
import logging


PathExceptions = List[str]
CallbackData = Union[ScheduleData, None]
FeedbackCallback = Callable[[str, CallbackData], Any]
# (FeedbackCommand.*              , Data)
# (FeedbackCommand.schedule_retry , (Seconds, State))
# (FeedbackCommand.release        , None)
# (FeedbackCommand.terminated     , None)


class FeedbackCommand:
    schedule_retry  = 'schedule_retry'
    release         = 'release'
    terminated      = 'terminated'


# local_src_path is root for local job,
# local_src_path/data is root for files 
# or dir to be uploaded.
# drive_dst_path is root for upload to google drive.
# ex. local_src_path=/home/john/.dormouse/job12
# drive_dst_path=photos/summer
# file local:/home/john/.dormouse/job12/data/img01.jpg
# will become gdrive:photos/summer/img01.jpg
# or file local:/home/john/.dormouse/job12/data/DCIM/img02.jpg
# will become gdrive:photos/summer/DCIM/img02.jpg
#
# local_src_path/.lock is lock file (to ensure unique access)
class FilesUploadJob:
    
    def __init__(self, drive: GoogleDrive, job_id: str,
                 local_src_path: Path, drive_dst_path: str,
                 feedback_callback: FeedbackCallback,
                 file_exceptions: PathExceptions = []):
        _name               = 'FUJ[{}]'.format(job_id) 
        self._log           = logging.getLogger(_name)
        self._total_files   = 0
        self._total_size    = 0
        self._drive         = drive
        self._job_id        = job_id
        self._lock_path     = os.path.abspath(local_src_path + '/.lock')
        self._src_path      = os.path.abspath(local_src_path + '/data')
        self._dst_path      = drive_dst_path
        self._callback      = feedback_callback
        self._state         = FilesUploadSM()
        self._file_except   = set(file_exceptions)
        self._lock          = None
        self._retry_state   = None
        self._relative_gdirs= {}
        self._photo_exts   = set(['jpg', 'jpeg', 'png', 'tif', 'tiff'])
        
        self._side_effects_handlers_map = {
            Command.lock_job      : self._lock_job,
            Command.unlock_job    : self._unlock_job,
            Command.open_session  : self._open_session,
            Command.close_session : self._close_session,
            Command.upload_file   : self._upload_file,
            Command.release_file  : self._release_file,
            Command.remove_data   : self._remove_data,
            Command.remove_job    : self._remove_job,
            Command.schedule_retry: self._schedule_retry,
            Command.release_sm    : self._release_sm}
        
        self._thread        = Thread(name=_name, target=self._run)
        
    @property
    def progress(self):
        return self._state.progress
        
    @property
    def total(self):
        return self._total_files, self._total_size
        
    def start(self, retry_state: State = None):
        self._retry_state = retry_state
        self._thread.start()
    
    def stop(self):
        try:
            self._cancel()
        except Exception as e:
            self._log.error('error canceling job %s', str(e))
        self._thread.join(timeout=30.0)
    
    def _run(self):
        self._log.info('job started')
        self._log.info('uploading from %s to GDrive:%s', 
                       self._src_path, self._dst_path)
        try:
            self._run_impl()
        except Exception as e:
            self._log.error('error during job execution %s', str(e))
            self._callback(FeedbackCommand.terminated, None)
        self._log.info('job finished')
        
    def _run_impl(self):
        if self._retry_state is None:
            self._run_first()
        else:
            state = self._retry_state
            self._retry_state = None
            self._run_retry(state)
            
    def _run_first(self):
        file_list = self._list_recursive(self._src_path)
        self._log.debug('job listed following files for upload:')
        for path, _ in file_list:
            self._log.debug(path)
        self._loop_side_effects(self._state.start(file_list))
        
    def _run_retry(self, state):
        self._log.debug('job retrying with state:')
        self._log.debug(str(state))
        self._loop_side_effects(self._state.retry(state))
        
    def _loop_side_effects(self, entry_side_effects):
        side_effects = entry_side_effects
        while len(side_effects) > 0:
            se = self._process_side_effects(side_effects)
            side_effects = se
            
    def _process_side_effects(self, side_effects):
        
        def execute_command(self, side_effect):
            cmd_map = self._side_effects_handlers_map
            command, data = side_effect
            self._log.debug('processing command (%s, %s)', 
                            command, str(data))
            if command in cmd_map:
                f = cmd_map[command]
                return f(command, data)
            self._log.warn('unknown command processing side effect:'
                           + ' (%s, %s)', command, str(data))
            return []
        
        ex = lambda se: execute_command(self, se)
        transformed = [ex(se) for se in side_effects]
        return reduce(lambda x, y: x + y, transformed, [])
        
    def _list_recursive(self, path: str):
        
        def filter_file(self, file_entry):
            not_in_except = file_entry.name not in self._file_except
            not_symlink = not file_entry.is_symlink()
            return not_in_except and not_symlink
                   
        entries = os.scandir(path)
        entries = [f for f in entries if filter_file(self, f)]
        files = [f for f in entries if f.is_file(follow_symlinks=False)]
        dirs  = [f for f in entries if f.is_dir(follow_symlinks=False)]
        entries = None
        
        def get_size(file_entry):
            stat = file_entry.stat(follow_symlinks=False)
            return stat.st_size 
            
        files = [(f.path, get_size(f)) for f in files]
        dirs  = [d.path for d in dirs]
        files_dirs = [self._list_recursive(path) for path in dirs]
        return reduce(lambda x, y: x + y, files_dirs, files)
        
    def _lock_job(self, _1, _2):
        if not os.path.exists(self._lock_path):
            return self._state.data_lock_failed_other()
        lock = None    
        try:
            lock = open(self._lock_path, 'w')
        except:
            return self._state.data_lock_failed_other()     
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock = lock
            return self._state.data_locked((self._lock_path, lock))
        except:
            lock.close()
            return self._state.data_lock_failed_taken() 
        
    def _unlock_job(self, _1, _2):
        self._free_lock()
        return self._state.data_unlocked()
        
    def _open_session(self, _1, _2):
        auth = self._drive.auth
        if not auth.access_token_expired:
            return self._state.session_opened((self._job_id, self._drive))
        try:
            auth.Refresh()
            return self._state.session_opened((self._job_id, self._drive))
        except RefreshError as e:
            self._log.error('error trying to refresh access token %s', 
                            str(e))
            return self._state.session_open_failed()
    
    def _close_session(self, _1, _2):
        return self._state.session_closed()
        
    def _upload_file(self, _, data: UploadData):
        sess_info, path = data
        _, drive = sess_info
        self._log.info('uploading file %s', path)
        try:
            return self._upload_file_impl(path, drive)
        except ApiRequestError as e:
            self._log.error('error uploading file %s', str(e))
            self._clear_gdrive_dir()
            return self._state.file_upload_failed(path)
        
    def _release_file(self, _, path: Path):
        try:
            os.remove(path)
        except Exception as e:
            self._log.error('error removing file %s: %s', path, str(e))
        return []
        
    def _remove_data(self, _1, _2):
        shutil.rmtree(self._src_path, ignore_errors=True)
        return self._state.data_removed()
        
    def _remove_job(self, _1, _2):
        path = os.path.dirname(self._src_path)
        shutil.rmtree(path, ignore_errors=True)
        return self._state.job_removed()
        
    def _schedule_retry(self, _, data: ScheduleData):
        try:
            self._callback(FeedbackCommand.schedule_retry, data)
        except Exception as e:
            self._log.error('error scheduling retry %s', str(e))
        return self._state.scheduled_retry()
        
    def _release_sm(self, _1, _2):
        try:
            self._callback(FeedbackCommand.release, None)
        except Exception as e:
            self._log.error('error releasing SM %s', str(e))
        return []
    
    def _upload_file_impl(self, path, drive):
        parent = self._get_gdrive_parent(drive, path)
        metadata = {
            'title'     : os.path.basename(path),
            'spaces'    : self._get_gdrive_spaces(path)}
        if parent is not None:
            metadata['parents'] = [parent]
        gfile = drive.CreateFile(metadata)
        gfile.SetContentFile(path)
        gfile.Upload()
        self._log.info('success uploading file %s', path)
        return self._state.file_uploaded(path)
        
    def _cancel(self):
        self._log.warn('cancel not implemented')
        
    def _free_lock(self):
        if self._lock is None:
            return
        fcntl.flock(self._lock, fcntl.LOCK_UN)
        try:
            self._lock.close()
        except:
            pass
        self._lock = None
        
    def _get_gdrive_parent(self, drive, path):
        dir_path = os.path.dirname(os.path.abspath(path))
        src_path = self._src_path
        if dir_path == src_path:
            return self._get_gdrive_root(drive)
        if not dir_path.startswith(src_path):
            raise RuntimeError('file from unexpected path'
                               + ' {}, root {}'.format(path, src_path))
        relative_dir = dir_path[len(src_path):]
        relative_dir = self._dst_path + relative_dir
        return self._get_gdrive_parent_cached(drive, relative_dir)

    def _get_gdrive_root(self, drive):
        dirs = self._dst_path.split(os.sep)
        dirs = [d for d in dirs if len(d) > 0]
        if len(dirs) == 0:
            return None
        return self._get_gdrive_parent_cached(drive, self._dst_path)
        
    def _get_gdrive_parent_cached(self, drive, gdrive_path):
        if gdrive_path in self._relative_gdirs:
            return self._relative_gdirs[gdrive_path]
        result = self._find_create_gdrive_dir(drive, gdrive_path)
        self._relative_gdirs[gdrive_path] = result
        return result

    def _find_create_gdrive_dir(self, drive, dir_path):
        dirs = dir_path.split(os.sep)
        dirs = [d for d in dirs if len(d) > 0]
        file_id = self._find_create_gdrive_dir_rec(drive, dirs, 'root')
        return {'kind': 'drive#fileLink', 'id': file_id}
        
    def _find_create_gdrive_dir_rec(self, drive, dirs, file_id):
        if len(dirs) == 0:
            return file_id
        lookup_name = dirs[0]
        query = "'{}' in parents and trashed=false".format(file_id)
        file_list = drive.ListFile({'q': query}).GetList()
        for f in file_list:
            if f['title'] == lookup_name:
                dirs = dirs[1:]
                return self._find_create_gdrive_dir_rec(drive, dirs, f['id'])
        return self._create_gdrive_mkdirs(drive, dirs, file_id)
        
    def _create_gdrive_mkdirs(self, drive, dirs, file_id):
        if len(dirs) == 0:
            return file_id
        dir_name = dirs[0]
        metadata = {
            'title'     : dir_name,
            'mimeType'  : 'application/vnd.google-apps.folder',
            'parents'   : [{'kind': 'drive#fileLink', 'id': file_id}]}
        new_dir = drive.CreateFile(metadata)
        new_dir.Upload()
        return self._create_gdrive_mkdirs(drive, dirs[1:], new_dir['id'])
        
    def _clear_gdrive_dir(self):
        self._relative_gdirs = {}
        
    def _get_gdrive_spaces(self, path):
        _, ext = os.path.splitext(path)
        if ext.startswith('.'):
            ext = ext[1:]
        ext = ext.lower()
        if ext in self._photo_exts:
            return ['drive', 'photos']
        return ['drive']
