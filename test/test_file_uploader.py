import unittest
from files_upload_sm import FilesUploadSM, Command
import logging as log


class TestFilesUploadSM(unittest.TestCase):

    def setUp(self):
        log.info('\n\nTest TestFilesUploadSM.%s started', self._testMethodName)

    def test_creation(self):
        obj = FilesUploadSM()
        self.assertEqual(obj.state, ('idle', 'idle'))
        
    def test_fine_empty(self):
        obj = FilesUploadSM()
        result = obj.start(list())
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:1>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_opened('<Session:1>')
        self.assertEqual(result, [(Command.close_session, '<Session:1>')])
        result = obj.session_closed()
        self.assertEqual(result, [(Command.remove_data, None)])
        result = obj.data_removed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:1>')])
        result = obj.data_unlocked()
        self.assertEqual(result, [(Command.remove_job, None)])
        result = obj.job_removed()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def test_fine_one(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:2>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_opened('<Session:2>')
        self.assertEqual(result, [(Command.upload_file, 
                                   ('<Session:2>', 'file1'))])
        result = obj.file_uploaded('file1')
        self.assertEqual(result, [(Command.release_file, 'file1'),
                                  (Command.close_session, '<Session:2>')])
        result = obj.session_closed()
        self.assertEqual(result, [(Command.remove_data, None)])
        result = obj.data_removed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:2>')])
        result = obj.data_unlocked()
        self.assertEqual(result, [(Command.remove_job, None)])
        result = obj.job_removed()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def test_fine_arr(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000),
                            ('file2', 600000),
                            ('file3', 900000),])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:2>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_opened('<Session:2>')
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file1 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:2>')
        result = obj.file_uploaded(file1)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file1))
        command, data = result.pop(0)
        session, file2 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:2>')
        result = obj.file_uploaded(file2)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file2))
        command, data = result.pop(0)
        session, file3 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:2>')
        result = obj.file_uploaded(file3)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file3))
        self.assertEqual(set([file1, file2, file3]),
                         set(['file1', 'file2', 'file3']))
        close_cmd = result.pop(0)
        self.assertEqual(close_cmd, (Command.close_session, '<Session:2>'))
        result = obj.session_closed()
        self.assertEqual(result, [(Command.remove_data, None)])
        result = obj.data_removed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:2>')])
        result = obj.data_unlocked()
        self.assertEqual(result, [(Command.remove_job, None)])
        result = obj.job_removed()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def test_fail_once_one(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:3>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_opened('<Session:3>')
        self.assertEqual(result, [(Command.upload_file, 
                                   ('<Session:3>', 'file1'))])
        result = obj.file_upload_failed('file1')
        self.assertEqual(result, [(Command.upload_file, 
                                   ('<Session:3>', 'file1'))])
        result = obj.file_uploaded('file1')
        self.assertEqual(result, [(Command.release_file, 'file1'),
                                  (Command.close_session, '<Session:3>')])
        result = obj.session_closed()
        self.assertEqual(result, [(Command.remove_data, None)])
        result = obj.data_removed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:3>')])
        result = obj.data_unlocked()
        self.assertEqual(result, [(Command.remove_job, None)])
        result = obj.job_removed()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def assertBetween(self, min_val, max_val, actual):
        self.assertTrue(min_val <= actual and actual <= max_val,
                        '{} <= {} <= {}'.format(min_val, actual, max_val))
        
    def test_fail_n_one(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:4>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_opened('<Session:4>')
        self.assertEqual(result, [(Command.upload_file, 
                                   ('<Session:4>', 'file1'))])
        result = obj.file_upload_failed('file1')
        self.assertEqual(result, [(Command.upload_file, 
                                   ('<Session:4>', 'file1'))])
        result = obj.file_upload_failed('file1')
        self.assertEqual(result, [(Command.upload_file, 
                                   ('<Session:4>', 'file1'))])
        result = obj.file_upload_failed('file1')
        self.assertEqual(result, [(Command.close_session, '<Session:4>')])
        result = obj.session_closed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:4>')])
        result = obj.data_unlocked()
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        seconds, _ = data
        self.assertEqual(command, Command.schedule_retry)
        self.assertBetween(30, 7 * 24 * 60 * 60, seconds)
        result = obj.scheduled_retry()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def test_fail_once_arr(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000), ('file2', 600000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:5>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_opened('<Session:5>')
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file1 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:5>')
        result = obj.file_upload_failed(file1)
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file2 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:5>')
        self.assertEqual(set([file1, file2]),
                         set(['file1', 'file2']))
        result = obj.file_upload_failed(file2)
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file3 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:5>')
        result = obj.file_uploaded(file3)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file3))
        command, data = result.pop(0)
        session, file4 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:5>')
        result = obj.file_uploaded(file4)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file4))
        self.assertEqual(set([file3, file4]),
                         set(['file1', 'file2']))
        close_cmd = result.pop(0)
        self.assertEqual(close_cmd, (Command.close_session, '<Session:5>'))
        result = obj.session_closed()
        self.assertEqual(result, [(Command.remove_data, None)])
        result = obj.data_removed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:5>')])
        result = obj.data_unlocked()
        self.assertEqual(result, [(Command.remove_job, None)])
        result = obj.job_removed()
        self.assertEqual(result, [(Command.release_sm, None)])

    def test_fail_session_open(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000), ('file2', 600000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:6>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_open_failed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:6>')])
        result = obj.data_unlocked()
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        seconds, _ = data
        self.assertEqual(command, Command.schedule_retry)
        self.assertBetween(30, 7 * 24 * 60 * 60, seconds)
        result = obj.scheduled_retry()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def test_fail_lock_taken(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000), ('file2', 600000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_lock_failed_taken()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def test_fail_lock_error(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000), ('file2', 600000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_lock_failed_other()
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        seconds, _ = data
        self.assertEqual(command, Command.schedule_retry)
        self.assertBetween(30, 7 * 24 * 60 * 60, seconds)
        result = obj.scheduled_retry()
        self.assertEqual(result, [(Command.release_sm, None)])

    def test_retry_session(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:6>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_open_failed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:6>')])
        result = obj.data_unlocked()
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        seconds, state = data
        self.assertEqual(command, Command.schedule_retry)
        self.assertBetween(30, 7 * 24 * 60 * 60, seconds)
        result = obj.scheduled_retry()
        self.assertEqual(result, [(Command.release_sm, None)])
        
        obj2 = FilesUploadSM()
        result = obj2.retry(state)
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj2.data_locked('<Lock:7>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj2.session_opened('<Session:7>')
        self.assertEqual(result, [(Command.upload_file, 
                                   ('<Session:7>', 'file1'))])
        result = obj2.file_uploaded('file1')
        self.assertEqual(result, [(Command.release_file, 'file1'),
                                  (Command.close_session, '<Session:7>')])
        result = obj2.session_closed()
        self.assertEqual(result, [(Command.remove_data, None)])
        result = obj2.data_removed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:7>')])
        result = obj2.data_unlocked()
        self.assertEqual(result, [(Command.remove_job, None)])
        result = obj2.job_removed()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def test_retry_upload(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000), ('file2', 400000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:8>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_opened('<Session:8>')
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file1 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:8>')
        result = obj.file_uploaded(file1)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file1))
        command, data = result.pop(0)
        session, file2 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:8>')
        result = obj.file_upload_failed(file2)
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file3 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:8>')
        result = obj.file_upload_failed(file3)
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file4 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:8>')
        result = obj.file_upload_failed(file4)
        self.assertEqual(file3, file2)
        self.assertEqual(file4, file2)
        self.assertEqual(set([file1, file2]),
                         set(['file1', 'file2']))
        self.assertEqual(result, [(Command.close_session, '<Session:8>')])
        result = obj.session_closed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:8>')])
        result = obj.data_unlocked()
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        seconds, state = data
        self.assertEqual(command, Command.schedule_retry)
        self.assertBetween(30, 7 * 24 * 60 * 60, seconds)
        result = obj.scheduled_retry()
        self.assertEqual(result, [(Command.release_sm, None)])
        
        obj2 = FilesUploadSM()
        result = obj2.retry(state)
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj2.data_locked('<Lock:9>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj2.session_opened('<Session:9>')
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file5 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:9>')
        result = obj2.file_upload_failed(file5)
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file6 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:9>')
        result = obj2.file_uploaded(file6)
        self.assertEqual(file5, file2)
        self.assertEqual(file6, file2)
        self.assertEqual(result, [(Command.release_file, file6),
                                  (Command.close_session, '<Session:9>')])
        result = obj2.session_closed()
        self.assertEqual(result, [(Command.remove_data, None)])
        result = obj2.data_removed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:9>')])
        result = obj2.data_unlocked()
        self.assertEqual(result, [(Command.remove_job, None)])
        result = obj2.job_removed()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def uploaded_helper_check(self, obj, file_name, dict_size,
                              session_name, acc_size):
        result = obj.file_uploaded(file_name)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file_name))
        command, data = result.pop(0)
        session, file2 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, session_name)
        size_file = dict_size[file_name]
        return file2, acc_size + size_file
        
    def assertAbout(self, expected, actual, dev): 
        min_expected = expected - dev/2.0
        max_expected = expected + dev/2.0
        self.assertTrue(min_expected < actual and actual < max_expected,
                        '{} < {} < {}'.format(min_expected, 
                                              actual, max_expected))
        
    def test_progress(self):
        
        def assertAbout0(self, prog_files, prog_size):
            self.assertTrue(0.0 <= prog_files)
            self.assertAbout(0.0, prog_files, 0.1)
            self.assertTrue(0.0 <= prog_size)
            self.assertAbout(0.0, prog_size, 0.1)
            
        def assertAbout1(self, prog_files, prog_size):
            self.assertTrue(1.0 >= prog_files)
            self.assertAbout(1.0, prog_files, 0.1)
            self.assertTrue(1.0 >= prog_size)
            self.assertAbout(1.0, prog_size, 0.1)
            
        def assertAboutVal(self, val, actual):
            self.assertAbout(val, actual, 0.1)
        
        obj = FilesUploadSM()
        dict_size = {'file1': 750000,
                     'file2': 600000,
                     'file3': 900000,
                     'file4': 350000}
        size_total = 750000 + 600000 + 900000 + 350000
        uploaded = lambda fn, acc: self.uploaded_helper_check(obj, fn, 
                                                              dict_size, 
                                                              '<sess:1>', 
                                                              acc)
        prog_files, prog_size = obj.progress
        assertAbout0(self, prog_files, prog_size)
        result = obj.start([('file1', 750000),
                            ('file2', 600000),
                            ('file3', 900000),
                            ('file4', 350000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        prog_files, prog_size = obj.progress
        assertAbout0(self, prog_files, prog_size)
        result = obj.data_locked('<Lock:10>')
        self.assertEqual(result, [(Command.open_session, None)])
        prog_files, prog_size = obj.progress
        assertAbout0(self, prog_files, prog_size)
        result = obj.session_opened('<sess:1>')
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file1 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<sess:1>')
        prog_files, prog_size = obj.progress
        assertAbout0(self, prog_files, prog_size)
        file2, size_done = uploaded(file1, 0)
        prog_files, prog_size = obj.progress
        assertAboutVal(self, 0.25, prog_files)
        assertAboutVal(self, size_done/size_total, prog_size)
        result = obj.file_upload_failed(file2)
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file2_2 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<sess:1>')
        prog_files, prog_size = obj.progress
        assertAboutVal(self, 0.25, prog_files)
        assertAboutVal(self, size_done/size_total, prog_size)
        file3, size_done = uploaded(file2_2, size_done)
        prog_files, prog_size = obj.progress
        assertAboutVal(self, 0.5, prog_files)
        assertAboutVal(self, size_done/size_total, prog_size)
        file4, size_done = uploaded(file3, size_done)
        prog_files, prog_size = obj.progress
        assertAboutVal(self, 0.75, prog_files)
        assertAboutVal(self, size_done/size_total, prog_size)
        result = obj.file_uploaded(file4)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file4))
        self.assertEqual(set([file1, file2, file2_2, file3, file4]),
                         set(['file1', 'file2', 'file3', 'file4']))
        close_cmd = result.pop(0)
        self.assertEqual(close_cmd, (Command.close_session, '<sess:1>'))
        prog_files, prog_size = obj.progress
        assertAbout1(self, prog_files, prog_size)
        result = obj.session_closed()
        self.assertEqual(result, [(Command.remove_data, None)])
        prog_files, prog_size = obj.progress
        assertAbout1(self, prog_files, prog_size)
        result = obj.data_removed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:10>')])
        prog_files, prog_size = obj.progress
        assertAbout1(self, prog_files, prog_size)
        result = obj.data_unlocked()
        self.assertEqual(result, [(Command.remove_job, None)])
        prog_files, prog_size = obj.progress
        assertAbout1(self, prog_files, prog_size)
        result = obj.job_removed()
        self.assertEqual(result, [(Command.release_sm, None)])
        
    def test_progress_after_retry(self):
        def assertAbout0(self, prog_files, prog_size):
            self.assertTrue(0.0 <= prog_files)
            self.assertAbout(0.0, prog_files, 0.1)
            self.assertTrue(0.0 <= prog_size)
            self.assertAbout(0.0, prog_size, 0.1)
            
        def assertAbout1(self, prog_files, prog_size):
            self.assertTrue(1.0 >= prog_files)
            self.assertAbout(1.0, prog_files, 0.1)
            self.assertTrue(1.0 >= prog_size)
            self.assertAbout(1.0, prog_size, 0.1)
            
        def assertAboutVal(self, val, actual):
            self.assertAbout(val, actual, 0.1)
        
        obj = FilesUploadSM()

        prog_files, prog_size = obj.progress
        assertAbout0(self, prog_files, prog_size)
        result = obj.start([('file1', 50000),
                            ('file2', 50000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        prog_files, prog_size = obj.progress
        assertAbout0(self, prog_files, prog_size)
        result = obj.data_locked('<Lock:11>')
        self.assertEqual(result, [(Command.open_session, None)])
        prog_files, prog_size = obj.progress
        assertAbout0(self, prog_files, prog_size)
        result = obj.session_opened('<sess:2>')
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file1 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<sess:2>')
        prog_files, prog_size = obj.progress
        assertAbout0(self, prog_files, prog_size)
        result = obj.file_uploaded(file1)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file1))
        command, data = result.pop(0)
        session, file2 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<sess:2>')
        prog_files, prog_size = obj.progress
        assertAboutVal(self, 0.5, prog_files)
        assertAboutVal(self, 0.5, prog_size)
        result = obj.file_upload_failed(file2)
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file3 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<sess:2>')
        prog_files, prog_size = obj.progress
        assertAboutVal(self, 0.5, prog_files)
        assertAboutVal(self, 0.5, prog_size)
        result = obj.file_upload_failed(file3)
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file4 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<sess:2>')
        prog_files, prog_size = obj.progress
        assertAboutVal(self, 0.5, prog_files)
        assertAboutVal(self, 0.5, prog_size)
        self.assertEqual(set([file2, file3, file4]),
                         set([file2]))
        self.assertEqual(set([file1, file2, file3, file4]),
                         set(['file1', 'file2']))
        result = obj.file_upload_failed(file4)
        self.assertEqual(result, [(Command.close_session, '<sess:2>')])
        result = obj.session_closed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:11>')])
        result = obj.data_unlocked()
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        seconds, state = data
        self.assertEqual(command, Command.schedule_retry)
        self.assertBetween(30, 7 * 24 * 60 * 60, seconds)
        result = obj.scheduled_retry()
        self.assertEqual(result, [(Command.release_sm, None)])
        prog_files, prog_size = obj.progress
        assertAboutVal(self, 0.5, prog_files)
        assertAboutVal(self, 0.5, prog_size)
        
        obj2 = FilesUploadSM()
        prog_files, prog_size = obj2.progress
        assertAbout0(self, prog_files, prog_size)
        result = obj2.retry(state)
        self.assertEqual(result, [(Command.lock_job, None)])
        prog_files, prog_size = obj2.progress
        assertAboutVal(self, 0.5, prog_files)
        assertAboutVal(self, 0.5, prog_size)
        result = obj2.data_locked('<Lock:12>')
        self.assertEqual(result, [(Command.open_session, None)])
        prog_files, prog_size = obj2.progress
        assertAboutVal(self, 0.5, prog_files)
        assertAboutVal(self, 0.5, prog_size)
        result = obj2.session_opened('<sess:3>')
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file5 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<sess:3>')
        result = obj2.file_uploaded(file5)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, (Command.release_file, file5))
        self.assertEqual(set([file1, file5]),
                         set(['file1', 'file2']))
        close_cmd = result.pop(0)
        self.assertEqual(close_cmd, (Command.close_session, '<sess:3>'))
        prog_files, prog_size = obj2.progress
        assertAbout1(self, prog_files, prog_size)
        result = obj2.session_closed()
        self.assertEqual(result, [(Command.remove_data, None)])
        prog_files, prog_size = obj2.progress
        assertAbout1(self, prog_files, prog_size)
        result = obj2.data_removed()
        self.assertEqual(result, [(Command.unlock_job, '<Lock:12>')])
        prog_files, prog_size = obj2.progress
        assertAbout1(self, prog_files, prog_size)
        result = obj2.data_unlocked()
        self.assertEqual(result, [(Command.remove_job, None)])
        prog_files, prog_size = obj2.progress
        assertAbout1(self, prog_files, prog_size)
        result = obj2.job_removed()
        self.assertEqual(result, [(Command.release_sm, None)])
        prog_files, prog_size = obj2.progress
        assertAbout1(self, prog_files, prog_size)
        
    def test_uploaded_wrong_file(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000), ('file2', 400000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:13>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_opened('<Session:4>')
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file1 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:4>')
        file2 = list(set(['file1', 'file2']) - set([file1]))[0]
        with self.assertRaises(ValueError):
            obj.file_uploaded(file2)
        
    def test_upload_failed_wrong_file(self):
        obj = FilesUploadSM()
        result = obj.start([('file1', 750000), ('file2', 400000)])
        self.assertEqual(result, [(Command.lock_job, None)])
        result = obj.data_locked('<Lock:14>')
        self.assertEqual(result, [(Command.open_session, None)])
        result = obj.session_opened('<Session:5>')
        self.assertEqual(len(result), 1)
        command, data = result.pop(0)
        session, file1 = data
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(session, '<Session:5>')
        file2 = list(set(['file1', 'file2']) - set([file1]))[0]
        with self.assertRaises(ValueError):
            obj.file_upload_failed(file2)
