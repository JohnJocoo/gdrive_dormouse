import sys

sys.path.append('src')

from status_bar_macos import MacOSBar
from status_bar_base import Status
from threading import Thread
import logging
import time

logger = logging.getLogger()
logger.level = logging.DEBUG
logger.addHandler(logging.StreamHandler(sys.stdout))

log = logging.getLogger('Test')


def callback(old_status, new_status):
    log.info('Status %s -> %s', old_status, new_status)
    
def run(bar):    
    time.sleep(1)
    bar.status = Status.idle
    time.sleep(10)
    bar.status = Status.auth_needed
    time.sleep(10)
    bar.status = Status.uploading
    for i in range(10):
        time.sleep(3)
        bar.progress = i/10.0
    bar.status = Status.idle
    time.sleep(10)


if __name__ == '__main__':
    bar = MacOSBar({}, callback)
    thread = Thread(name = 'AppThread', 
                    target = lambda : run(bar))
    thread.start()
    bar.run()
    
