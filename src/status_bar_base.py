from typing import Callable, Any
from queue import Queue, Empty
from concurrent.futures import Future
import logging
import abc


class Status:
    idle        = 'idle'
    uploading   = 'uploading'
    paused      = 'paused'
    auth_needed = 'auth_needed'


StatusCallback = Callable[[Status, Status], Any]


class StatusBarBase:
    
    def __init__(self, config, status_callback: StatusCallback):
        self._config = config
        self._callback = status_callback
        self._progress = 0.0
        self._status = Status.idle
        self._events_queue = Queue()
        self._log = logging.getLogger('StatusBar')
        
    @property
    def priv_name(self):
        return 'GDriveDormouse'
        
    @property
    def name(self):
        future = Future()
        self._events_queue.put(lambda : future.set_result(self.priv_name), timeout=5)
        return future.result(timeout=5)
        
    @property
    def priv_status(self) -> Status:
        return self._status
        
    @property
    def status(self) -> Status:
        future = Future()
        self._events_queue.put(lambda : future.set_result(self.priv_status), timeout=5)
        return future.result(timeout=5)
        
    @priv_status.setter
    def priv_status(self, status: Status):
        if self._status == status:
            return
        old_status = self._status
        try:
            self._status = status
            self._events_queue.put(lambda : self._update(), timeout=5)
        finally:
            self._log.info('status changed %s -> %s', old_status, status)
            self._callback(old_status, status)
    
    @status.setter
    def status(self, status: Status):
        
        def set_priv_status(status):
            self.priv_status = status
            
        self._events_queue.put(lambda : set_priv_status(status), timeout=5)

    @property
    def priv_config(self):
        return self._config

    @property
    def config(self):
        future = Future()
        self._events_queue.put(lambda : future.set_result(self.priv_config), timeout=5)
        return future.result(timeout=5)
        
    @priv_config.setter
    def priv_config(self, config):
        self._config = config
        self._update()
        
    @config.setter
    def config(self, config):
        self._events_queue.put(lambda : self.priv_config = config, timeout=5)
        
    @property
    def priv_progress(self):
        return self._progress
        
    @property
    def progress(self):
        future = Future()
        self._events_queue.put(lambda : future.set_result(self.priv_progress), timeout=5)
        return future.result(timeout=5)
       
    @priv_progress.setter
    def priv_progress(self, value):
        self._progress = value
        self._update()
        
    @progress.setter
    def progress(self, value):
        if not isinstance(value, float):
            raise ValueError()
        if value < 0.0:
            value = 0.0
        elif value > 1.0:
            value = 1.0
        self._events_queue.put(lambda : self.priv_progress = value, timeout=5)
        
    @abc.abstractmethod
    def _update(self):
        pass
      
    @abc.abstractmethod
    def run(self):
        pass
        
    def process_events(self):
        while not self._events_queue.empty():
            try:
                self._events_queue.get(block=True, timeout=1)()
            except Empty:
                pass
            except Exception as e:
                self._log.error('Exception processing event %s', str(e))
