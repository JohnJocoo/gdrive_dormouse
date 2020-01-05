import unittest
from files_upload_job import FilesUploadJob, FeedbackCommand
import logging as log
import random
import string
import os
from os.path import join as fs_join
import shutil
import fcntl
from ddt import ddt, data
from GDriveFileMock import GDriveFileMock, ListFileResult
from GDriveMock import GDriveMock
from GAuthMock import GAuthMock
from CommandCallbackMock import CommandCallbackMock
from files_upload_sm import Command


@ddt
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
        with open(path, 'w+') as f:
            f.write(data)
            
    def _create_random_file(self, path, size = 256):
        letters = string.ascii_lowercase
        data = ''.join(random.choice(letters) for i in range(size))
        self._create_file(path, data)

    def _create_job_empty(self):
        job_id = self._generate_job_id()
        job_dir = fs_join(self._get_data_dir(), job_id)
        os.makedirs(job_dir)
        self._touch(fs_join(job_dir, '.lock'))
        data_dir = fs_join(job_dir, 'data')
        os.makedirs(data_dir)
        return job_id, data_dir, []
        
    def _create_job_one_file(self):
        job_id, data_dir, _ = self._create_job_empty()
        file_path = fs_join(data_dir, 'cool_file.txt')
        self._create_random_file(file_path)
        return job_id, data_dir, [(file_path, 'file')]
        
    def _create_job_mixed(self):
        job_id, data_dir, _ = self._create_job_empty()
        
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
    
    def _create_job(self, scenario):
        func = getattr(self, '_create_job_' + scenario)
        return func()
        
    def _delete_job(self, job_id):
        job_dir = fs_join(self._get_data_dir(), job_id)
        shutil.rmtree(job_dir, ignore_errors=True)

    def _create_default_upload_job(self, job_id, dst_dir = ''):
        drive = GDriveMock(GAuthMock())
        job_dir = fs_join(self._get_data_dir(), job_id)
        callback = CommandCallbackMock()
        job = FilesUploadJob(drive, job_id, job_dir, dst_dir, callback)
        return job, drive, callback
        
    def _mock_side_effects_handlers(self, job):
        job.commands_history_mocked = []
        
        def call_callback(callback, cmd, data):
            job.commands_history_mocked.append(cmd)
            return callback(cmd, data)
        
        def mocked_cb(callback):
            return lambda cmd, data: call_callback(callback, cmd, data)
        
        h_map = job._side_effects_handlers_map
        new_map = {cmd: mocked_cb(cb) for cmd, cb in h_map.items()}
        job._side_effects_handlers_map = new_map
        return job

    def setUp(self):
        data_dir = self._get_data_dir()
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir, ignore_errors=False)
        os.makedirs(data_dir)

    def tearDown(self):
        data_dir = self._get_data_dir()
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir, ignore_errors=False)
            
    @data('empty', 'one_file', 'mixed')
    def test_list(self, scenario):
        job_id, data_dir, fs_list = self._create_job(scenario)
        job, _, _ = self._create_default_upload_job(job_id)
        list_result = job._list_recursive(data_dir)
        files_expected = set([f for f, t in fs_list if t == 'file'])
        files = set([f for f, _ in list_result])
        self.assertEqual(files, files_expected)
        self._delete_job(job_id)
        
    def test_lock_taken(self):
        job_id, data_dir, _ = self._create_job('empty')
        job, drive, callback = self._create_default_upload_job(job_id)
        job = self._mock_side_effects_handlers(job)
        lock_path = fs_join(os.path.dirname(data_dir), '.lock')
        lock = open(lock_path, 'w')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        job._run_impl()
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        self.assertEqual(job.commands_history_mocked, 
                         [Command.lock_job, Command.release_sm])
        drive.auth.Refresh.assert_not_called()
        drive.CreateFile.assert_not_called()
        drive.ListFile.assert_not_called()
        callback.called.assert_called_once_with(FeedbackCommand.release, None)
        self._delete_job(job_id)
        
    def test_session_refresh(self):
        job_id, _, _ = self._create_job('empty')
        job, drive, callback = self._create_default_upload_job(job_id)
        job = self._mock_side_effects_handlers(job)
        drive.auth.access_token_expired = True
        job._run_impl()
        drive.auth.Refresh.assert_called()
        self.assertEqual(job.commands_history_mocked, 
                         [Command.lock_job, Command.open_session, 
                          Command.close_session, Command.remove_data, 
                          Command.unlock_job, Command.remove_job, 
                          Command.release_sm])
        drive.CreateFile.assert_not_called()
        drive.ListFile.assert_not_called()
        callback.called.assert_called_once_with(FeedbackCommand.release, None)
        self._delete_job(job_id)
        
    @data('empty', 'one_file', 'mixed')
    def test_success_flow(self, scenario):
        job_id, _, fs_list = self._create_job(scenario)
        job, drive, callback = self._create_default_upload_job(job_id)
        job = self._mock_side_effects_handlers(job)
        job._run_impl()
        history = job.commands_history_mocked
        self.assertEqual(history[:2], [Command.lock_job, 
                                       Command.open_session])
        self.assertEqual(history[-5:], [Command.close_session, 
                                        Command.remove_data, 
                                        Command.unlock_job, 
                                        Command.remove_job, 
                                        Command.release_sm])
        if len(fs_list) > 0:
            self.assertEqual(set(history[2:-5]), 
                             set([Command.upload_file, 
                                  Command.release_file]))
        if len(fs_list) > 0:
            drive.CreateFile.assert_called()
        callback.called.assert_called_once_with(FeedbackCommand.release, None)
        drive.auth.Refresh.assert_not_called()
        self._delete_job(job_id)
        
    def test_success_flow_detailed(self):
        job_id, _, fs_list = self._create_job('one_file')
        job, drive, callback = self._create_default_upload_job(job_id)
        job = self._mock_side_effects_handlers(job)
        self.assertEqual(len(fs_list), 1)
        file_path, _ = fs_list[0]
        created_files = []
        create_file_saved_se = drive.CreateFile.side_effect
        
        def create_file_se(*args, **kwargs):
            mock_file = create_file_saved_se(*args, **kwargs)
            created_files.append(mock_file)
            return mock_file
        
        drive.CreateFile.side_effect = create_file_se
        job._run_impl()
        history = job.commands_history_mocked
        self.assertEqual(history, [Command.lock_job, 
                                   Command.open_session,
                                   Command.upload_file,
                                   Command.release_file,
                                   Command.close_session, 
                                   Command.remove_data, 
                                   Command.unlock_job, 
                                   Command.remove_job, 
                                   Command.release_sm])
        drive.CreateFile.assert_called_once()
        self.assertEqual(len(created_files), 1)
        created_file = created_files[0]
        self.assertEqual(created_file['title'], 'cool_file.txt')
        self.assertEqual(created_file['spaces'], ['drive'])
        self.assertFalse(created_file.has_item('parents'))
        created_file.SetContentFile.assert_called_once_with(file_path)
        created_file.Upload.assert_called_once()
        callback.called.assert_called_once_with(FeedbackCommand.release, None)
        drive.auth.Refresh.assert_not_called()
        self._delete_job(job_id)
        
    def test_success_flow_detailed_one_dir(self):
        job_id, data_dir, _ = self._create_job_empty()
        dir1_path = fs_join(data_dir, 'photos')
        file_path = fs_join(dir1_path, 'IMG_0345.jpg')
        os.makedirs(dir1_path)
        self._create_random_file(file_path, 820000)
        job, drive, callback = self._create_default_upload_job(job_id)
        job = self._mock_side_effects_handlers(job)
        created_files = []
        create_file_saved_se = drive.CreateFile.side_effect
        
        def create_file_se(*args, **kwargs):
            mock_file = create_file_saved_se(*args, **kwargs)
            created_files.append(mock_file)
            return mock_file
        
        drive.CreateFile.side_effect = create_file_se
        job._run_impl()
        history = job.commands_history_mocked
        self.assertEqual(history, [Command.lock_job, 
                                   Command.open_session,
                                   Command.upload_file,
                                   Command.release_file,
                                   Command.close_session, 
                                   Command.remove_data, 
                                   Command.unlock_job, 
                                   Command.remove_job, 
                                   Command.release_sm])
        drive.CreateFile.assert_called()
        self.assertEqual(len(created_files), 2)
        created_dir = created_files[0]
        created_file = created_files[1]
        self.assertEqual(created_dir['title'], 'photos')
        self.assertEqual(created_dir['mimeType'], 
                         'application/vnd.google-apps.folder')
        self.assertEqual(created_dir['parents'], 
                         [{'kind': 'drive#fileLink', 'id': 'root'}])
        self.assertEqual(created_file['title'], 'IMG_0345.jpg')
        self.assertEqual(set(created_file['spaces']), 
                         set(['drive', 'photos']))
        self.assertEqual(created_file['parents'], 
                         [{'kind': 'drive#fileLink', 
                           'id': created_dir['id']}])
        created_dir.Upload.assert_called_once()
        created_file.SetContentFile.assert_called_once_with(file_path)
        created_file.Upload.assert_called_once()
        callback.called.assert_called_once_with(FeedbackCommand.release, None)
        drive.auth.Refresh.assert_not_called()
        self._delete_job(job_id)
        
    def test_upload_fail_flow(self):
        pass
        
    def test_upload_fail_once_flow(self):
        pass
        
    def test_spaces_detection(self):
        job_id, _, _ = self._create_job('empty')
        job, _, _ = self._create_default_upload_job(job_id)
        spaces = job._get_gdrive_spaces('/tmp/file.txt')
        self.assertEqual(spaces, ['drive'])
        spaces = job._get_gdrive_spaces('/tmp/IMG_0342.JPG')
        self.assertEqual(set(spaces), set(['drive', 'photos']))
        spaces = job._get_gdrive_spaces('/tmp/IMG_0342.jpeg')
        self.assertEqual(set(spaces), set(['drive', 'photos']))
        spaces = job._get_gdrive_spaces('/tmp/my_cat.png')
        self.assertEqual(set(spaces), set(['drive', 'photos']))
        spaces = job._get_gdrive_spaces('/tmp/my_cat.01.spain.jpg')
        self.assertEqual(set(spaces), set(['drive', 'photos']))
        spaces = job._get_gdrive_spaces('/tmp/file_pict')
        self.assertEqual(spaces, ['drive'])
        spaces = job._get_gdrive_spaces('/tmp/my_cat.jpg.zip')
        self.assertEqual(spaces, ['drive'])
        self._delete_job(job_id)
