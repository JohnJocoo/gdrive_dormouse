import unittest
from files_upload_job import FilesUploadJob, FeedbackCommand
import logging as log
import random
import string
import os
from os.path import join as fs_join
import shutil


class TestFilesUploadJob(unittest.TestCase):
    _data_dir = 'tmp_test_data'
    

    def _get_data_dir(self):
        return os.path.abspath(fs_join(os.getcwd(), self._data_dir))

    def _generate_job_id(self, length = 16):
        letters = string.ascii_lowercase + string.digits
        return ''.join(random.choice(letters) for i in range(length))

    def _touch(self, path):
        with open(path, 'a'):
            pass
            
    def _create_file(self, path, data):
        with open(path, 'w') as f:
            f.write(data)
            
    def _create_random_file(self, path, size = 256):
        letters = string.ascii
        data = ''.join(random.choice(letters) for i in range(size))
        self._create_file(path, data)

    def _create_job_empty(self):
        job_id = self._generate_job_id()
        job_dir = fs_join(self._get_data_dir(), job_id)
        os.makedirs(job_dir)
        self._touch(fs_join(job_dir, '.lock'))
        data_dir = fs_join(job_dir, 'data')
        return job_id, data_dir
        
    def _create_job_one_file(self):
        job_id, data_dir = self._create_job_empty()
        file_path = fs_join(data_dir, 'cool_file.txt')
        self._create_random_file(file_path)
        return job_id, data_dir, [(file_path, 'file')]
        
    def _create_job_mixed(self):
        job_id, data_dir = self._create_job_empty()
        
        dir1 = fs_join(data_dir, 'personal')
        dir2 = fs_join(dir1, 'photos')
        dir3 = fs_join(dir2, 'jpeg')
        dir4 = fs_join(dir2, 'raw')
        dir5 = fs_join(data_dir, 'docs')
        
        file1 = fs_join(data_dir, 'my_text.txt')
        file2 = fs_join(data_dir, 'my_cat.jpeg')
        file3 = fs_join(dir3, 'img_01.jpg')
        file4 = fs_join(dir3, 'img_02.jpg')
        file5 = fs_join(dir3, 'img_03.jpg')
        file6 = fs_join(dir1, 'some_file.txt')
        file7 = fs_join(dir1, 'img.png')
        file8 = fs_join(dir5, 'important.txt')
        
        os.makedirs(dir1)
        os.makedirs(dir2)
        os.makedirs(dir3)
        os.makedirs(dir4)
        os.makedirs(dir5)
        
        self._create_random_file(file1)
        self._create_random_file(file2, 50000)
        self._create_random_file(file3, 200000)
        self._create_random_file(file4, 300000)
        self._create_random_file(file5, 400000)
        self._create_random_file(file6)
        self._create_random_file(file7)
        self._create_random_file(file8)
        
        result_list = [(dir1,   'dir'),
                       (dir2,   'dir'),
                       (dir3,   'dir'),
                       (dir4,   'dir'),
                       (dir5,   'dir'),
                       (file1,  'file'),
                       (file2,  'file'),
                       (file3,  'file'),
                       (file4,  'file'),
                       (file5,  'file'),
                       (file6,  'file'),
                       (file7,  'file'),
                       (file8,  'file')]
        return job_id, data_dir, result_list
        
    def _delete_job(self, job_id):
        job_dir = fs_join(self._get_data_dir(), job_id)
        shutil.rmtree(job_dir, ignore_errors=True)

    def setUp(self):
        data_dir = self._get_data_dir()
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir, ignore_errors=False)
        os.makedirs(data_dir)

    def tearDown(self):
        data_dir = self._get_data_dir()
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir, ignore_errors=False)
    
