import unittest
import sys
import logging

sys.path.append('../src')

from test_file_uploader_sub_sm import *
from test_file_uploader import *
from test_file_upload_job import *


logger = logging.getLogger()
logger.level = logging.DEBUG
logger.addHandler(logging.StreamHandler(sys.stdout))


if __name__ == '__main__':
    unittest.main()
    
