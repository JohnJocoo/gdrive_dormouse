from typing import List, Tuple, Union, Any
from functools import reduce
from collections import deque
import xworkflows
import logging as log


Path = str
Size = int # size bytes
Seconds = int
FileEntry = Tuple[Path, Size]
State = Any
Lock = Any
Session = Any
CommandT = str # Use Command (ex. Command.lock_job)
ScheduleData = Tuple[Seconds, State]
UploadData = Tuple[Session, Path]
CommandData = Union[Lock, Session, Path, UploadData, ScheduleData, None]
SideEffect = Tuple[CommandT, CommandData]
# (Command.*              , Data)
# (Command.lock_job       , None)
# (Command.unlock_job     , Lock)
# (Command.open_session   , None)
# (Command.close_session  , Session)
# (Command.upload_file    , (Session, Path))
# (Command.release_file   , Path)
# (Command.remove_data    , None)
# (Command.remove_job     , None)
# (Command.schedule_retry , (Seconds, State))
# (Command.release_sm     , None)
SideEffects = List[SideEffect]


class Command:
    lock_job        = 'lock_job'
    unlock_job      = 'unlock_job'
    open_session    = 'open_session'
    close_session   = 'close_session'
    upload_file     = 'upload_file'
    release_file    = 'release_file'
    remove_data     = 'remove_data'
    remove_job      = 'remove_job'
    schedule_retry  = 'schedule_retry'
    release_sm      = 'release_sm'


class FilesUploadWorkflow(xworkflows.Workflow):
    
    states = (
        ('idle',                'Initial state'),
        ('locking',             'Trying to acquire unique lock for job'),
        ('opening_session',     'Opening remote session'),
        ('uploading',           'Uploading files to remote'),
        ('closing_session',     'Closing remote session'),
        ('removing_data',       'Removing jobs data (job succeed)'),
        ('unlocking',           'Unlocking session (job succeed)'),
        ('removing_job',        'Removing job (success)'),
        ('done',                'Done'),
        ('closing_sess_retry',  'Closing remote session (job failed)'),
        ('unlocking_retry',     'Unlocking session (job failed)'),
        ('scheduling_retry',    'Scheduling retry (job failed)'),
    )

    transitions = (
        ('start',           'idle',             'locking'),
        ('retry',           'idle',             'locking'),
        ('data_locked',     'locking',          'opening_session'),
        ('session_opened',  'opening_session',  'uploading'),
        ('upload_done_all', 'uploading',        'closing_session'),
        ('session_closed',  'closing_session',  'removing_data'),
        ('data_removed',    'removing_data',    'unlocking'),
        ('data_unlocked',   'unlocking',        'removing_job'),
        ('job_removed',     'removing_job',     'done'),
        
        ('session_open_failed',  'opening_session',    'unlocking_retry'),
        ('upload_error',         'uploading',          'closing_sess_retry'),
        ('session_closed_retry', 'closing_sess_retry', 'unlocking_retry'),
        ('data_unlocked_retry',  'unlocking_retry',    'scheduling_retry'),
        ('scheduled_retry',      'scheduling_retry',   'done'),
        
        ('data_lock_failed_taken','locking',          'done'),
        ('data_lock_failed_other','locking',          'scheduling_retry'),
    )

    initial_state = 'idle'
    
    
    def log_transition(_, transition, from_state, *args, **kwargs):
        log.debug('FilesUploadSM transition <%s> from <%s> to <%s>',
                  str(transition.name), 
                  str(from_state), 
                  str(transition.target))
    
    
class FilesUploadSubWorkflow(xworkflows.Workflow):
    
    states = (
        ('idle',                'Initial state'),
        ('uploading_file',      'Uploading one file to remote'),
        ('done',                'Done'),
    )

    transitions = (
        ('start_not_empty',         'idle',           'uploading_file'),
        ('start_empty',             'idle',           'done'),
        ('uploaded_ok_not_empty',   'uploading_file', 'uploading_file'),
        ('uploaded_ok_empty',       'uploading_file', 'done'),
        ('upload_err_retry',        'uploading_file', 'uploading_file'),
        ('upload_err_final',        'uploading_file', 'done'),
    )

    initial_state = 'idle'


    def log_transition(_, transition, from_state, *args, **kwargs):
        log.debug('FilesUploadSubState transition <%s> from <%s> to <%s>',
                  str(transition.name), 
                  str(from_state), 
                  str(transition.target))
    

class FilesUploadSubState(xworkflows.WorkflowEnabled):
    
    _state = FilesUploadSubWorkflow()
    
    
    def __init__(self):
        self._files          = deque() # [(Path, RetriesLeft)]
        self._current_file   = None
    
    @property
    def _retries(self):
        return 2
        
    @property
    def state(self):
        return str(self._state)
        
    def start(self, file_list: List[FileEntry]) -> SideEffects:
        self._files = deque([(path, self._retries) 
                             for path, _ in file_list])
        if len(self._files) == 0:
            return self._start_empty()
        return self._start_not_empty()
        
    def upload_succeed(self, file_path: Path) -> SideEffects:
        self._remove_file(file_path)
        result = [(Command.release_file, file_path)]
        if len(self._files) == 0:
            return result + self._uploaded_ok_empty()
        return result + self._uploaded_ok_not_empty()
        
    def upload_failed(self, file_path: Path) -> SideEffects:
        if self._can_retry(file_path):
            return self._upload_err_retry(file_path)
        return self._upload_err_final(file_path)
        
    def _check_current_file(self, file_path: Path):
        path, _ = self._current_file
        if path != file_path:
            raise ValueError('Unexpected FilePath')
        
    def _remove_file(self, file_path: Path):
        self._check_current_file(file_path)
        path, _ = self._current_file
        self._current_file = None
        
    def _can_retry(self, file_path: Path):
        self._check_current_file(file_path)
        path, retries = self._current_file
        return retries > 0
        
    def _next(self):
        self._current_file = self._files.popleft()
        path, _ = self._current_file
        return path
        
    @xworkflows.transition('start_empty')
    def _start_empty(self):
        return [('_empty', None)]
    
    @xworkflows.transition('start_not_empty')    
    def _start_not_empty(self):
        path = self._next()
        return [(Command.upload_file, path)]
        
    @xworkflows.transition('uploaded_ok_empty')
    def _uploaded_ok_empty(self):
        return [('_empty', None)]
    
    @xworkflows.transition('uploaded_ok_not_empty')    
    def _uploaded_ok_not_empty(self):
        path = self._next()
        return [(Command.upload_file, path)]
    
    @xworkflows.transition('upload_err_retry')    
    def _upload_err_retry(self, file_path):
        self._check_current_file(file_path)
        path, retries = self._current_file
        self._current_file = None
        self._files.append((path, retries - 1))
        path = self._next()
        return [(Command.upload_file, path)]
        
    @xworkflows.transition('upload_err_final')
    def _upload_err_final(self, file_path):
        self._check_current_file(file_path)
        return [('_final_error', file_path)]


class FilesUploadSM(xworkflows.WorkflowEnabled):    
    
    _state = FilesUploadWorkflow()
    
    
    def __init__(self):
        self._files_state    = FilesUploadSubState()
        
        self._files          = dict()
        self._files_original = dict()
        self._total_size     = 0
        self._uploaded_size  = 0
        self._lock           = None
        self._session        = None
        
        self._retry_seconds  = 5 * 60
        self._sub_sm_side_effects_handlers_map = {
            Command.upload_file : self._handle_sub_sm_upload,
            Command.release_file: self._handle_sub_sm_release,
            '_empty'            : self._handle_sub_sm_empty,
            '_final_error'      : self._handle_sub_sm_final_error}
    
    @property
    def state(self):
        return str(self._state), self._files_state.state
        
    @property
    def progress(self):
        num_files_all = len(self._files_original)
        num_files_done = num_files_all - len(self._files)
        if num_files_all == 0 or self._total_size == 0:
            return 0.0, 0.0
        progress_files = num_files_done / num_files_all
        progress_size = self._uploaded_size / self._total_size
        return float(progress_files), float(progress_size)
    
    @xworkflows.transition('start')
    def start(self, file_list: List[FileEntry]) -> SideEffects:
        total_size = self._calculate_size(file_list)
        self._files_original = {f: (f, d) for f, d in file_list}
        self._files = self._files_original.copy()
        self._total_size = total_size
        _uploaded_size = 0
        return [(Command.lock_job, None)]
        
    @xworkflows.transition('retry')
    def retry(self, state: State) -> SideEffects:
        self.__setstate__(state)
        return [(Command.lock_job, None)]
       
    @xworkflows.transition('data_locked')
    def data_locked(self, lock: Lock) -> SideEffects:
        self._lock = lock
        return [(Command.open_session, None)]
        
    @xworkflows.transition('data_lock_failed_taken')
    def data_lock_failed_taken(self) -> SideEffects:
        return [(Command.release_sm, None)]
        
    @xworkflows.transition('data_lock_failed_other')
    def data_lock_failed_other(self) -> SideEffects:
        state = self.__getstate__()
        return [(Command.schedule_retry, 
                 (self._retry_seconds, state))]
        
    def session_opened(self, session: Session) -> SideEffects:
        result = self._session_opened(session)
        files = list(self._files.values())
        side_effects = self._files_state.start(files)
        return result + self._handle_sub_sm_side_effects(side_effects)
        
    @xworkflows.transition('session_open_failed')
    def session_open_failed(self) -> SideEffects:
        lock = self._lock
        self._lock = None
        return [(Command.unlock_job, lock)]
    
    def file_uploaded(self, file_path: Path) -> SideEffects:
        side_effects = self._files_state.upload_succeed(file_path)
        return self._handle_sub_sm_side_effects(side_effects)
        
    def file_upload_failed(self, file_path: Path) -> SideEffects:
        side_effects = self._files_state.upload_failed(file_path)
        return self._handle_sub_sm_side_effects(side_effects)
        
    def session_closed(self) -> SideEffects:
        if self._state == 'closing_sess_retry':
            return self._session_closed_retry()
        return self._session_closed()
        
    @xworkflows.transition('data_removed')
    def data_removed(self) -> SideEffects:
        lock = self._lock
        self._lock = None
        return [(Command.unlock_job, lock)]
    
    def data_unlocked(self) -> SideEffects:
        if self._state == 'unlocking_retry':
            return self._data_unlocked_retry()
        return self._data_unlocked()
        
    @xworkflows.transition('job_removed')
    def job_removed(self) -> SideEffects:
        return [(Command.release_sm, None)]
    
    @xworkflows.transition('scheduled_retry')
    def scheduled_retry(self) -> SideEffects:
        return [(Command.release_sm, None)]
        
    @xworkflows.transition('session_opened')
    def _session_opened(self, session: Session):
        self._session = session
        return []
        
    @xworkflows.transition('upload_done_all')
    def _upload_done_all(self):
        session = self._session
        self._session = None
        return [(Command.close_session, session)]
        
    @xworkflows.transition('upload_error')
    def _upload_error(self):
        session = self._session
        self._session = None
        return [(Command.close_session, session)]
        
    @xworkflows.transition('session_closed')
    def _session_closed(self):
        return [(Command.remove_data, None)]
        
    @xworkflows.transition('session_closed_retry')
    def _session_closed_retry(self):
        lock = self._lock
        self._lock = None
        return [(Command.unlock_job, lock)]
        
    @xworkflows.transition('data_unlocked')
    def _data_unlocked(self):
        return [(Command.remove_job, None)]
        
    @xworkflows.transition('data_unlocked_retry')
    def _data_unlocked_retry(self):
        state = self.__getstate__()
        return [(Command.schedule_retry, 
                 (self._retry_seconds, state))]
        
    def _handle_sub_sm_side_effects(
        self, side_effects: SideEffects) -> SideEffects:
            
        def execute_command(cmd_map, side_effect):
            command, data = side_effect
            if command in cmd_map:
                f = cmd_map[command]
                return f(command, data)
            return [(command, data)]
        
        cmd_map = self._sub_sm_side_effects_handlers_map
        ex = lambda se: execute_command(cmd_map, se)
        transformed = [ex(se) for se in side_effects]
        return reduce(lambda x, y: x + y, transformed, [])
        
    def _handle_sub_sm_upload(self, _, file_path):
        return [(Command.upload_file, (self._session, file_path))]
        
    def _handle_sub_sm_release(self, _, file_path):
        if file_path in self._files:
            _, size = self._files[file_path]
            self._uploaded_size += size
            del self._files[file_path]
        return [(Command.release_file, file_path)]
        
    def _handle_sub_sm_empty(self, _, _2):
        return self._upload_done_all()
        
    def _handle_sub_sm_final_error(self, _, _2):
        return self._upload_error()
        
    def _calculate_size(self, file_list: List[FileEntry]) -> int:
        total_size = reduce(
            lambda x, y: x + y, 
            [i for _, i in file_list],
            0)
        return total_size

    def __getstate__(self):
        return {
            'class': 'FilesUploadSM',
            'files': self._files,
            'files_original': self._files_original}

    def __setstate__(self, state):
        files = state['files']
        files_original = state['files_original']
        total_size = self._calculate_size(files_original.values())
        remains_size = self._calculate_size(files.values())
        self._files = dict(files)
        self._files_original = dict(files_original)
        self._total_size = total_size
        self._uploaded_size = total_size - remains_size
