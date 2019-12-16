import unittest
from files_upload_sm import FilesUploadSubState, Command
import logging as log


class TestFilesUploadSubState(unittest.TestCase):

    def setUp(self):
        log.info('\n\nTest TestFilesUploadSubState.%s started', self._testMethodName)

    def test_creation(self):
        obj = FilesUploadSubState()
        self.assertEqual(obj.state, 'idle')
        
    def test_start_empty(self):
        obj = FilesUploadSubState()
        result = obj.start(list())
        self.assertEqual(result, [('_empty', None)])

    def test_start_one(self):
        obj = FilesUploadSubState()
        result = obj.start([('file1', 600000)])
        self.assertEqual(result, [(Command.upload_file, 'file1')])
        
    def test_start_arr(self):
        obj = FilesUploadSubState()
        arr = [('file1', 600000), ('file2', 750000), ('file3', 1000000)]
        result = obj.start(arr)
        self.assertEqual(result, [(Command.upload_file, 'file1')])    
        
    def test_fine_one(self):
        obj = FilesUploadSubState()
        result = obj.start([('file1', 600000)])
        self.assertEqual(len(result), 1)
        command, file_name = result.pop()
        self.assertEqual(command, Command.upload_file)
        result = obj.upload_succeed(file_name)
        self.assertEqual(result, [(Command.release_file, file_name), 
                                  ('_empty', None)]) 
        
    def test_fine_arr(self):
        obj = FilesUploadSubState()
        arr = [('file1', 600000), ('file2', 750000), ('file3', 1000000)]
        result = obj.start(arr)
        self.assertEqual(len(result), 1)
        command, file_name = result.pop()
        self.assertEqual(command, Command.upload_file)
        result = obj.upload_succeed(file_name)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, 
                         (Command.release_file, file_name))
        command, file_name2 = result.pop(0)
        self.assertEqual(command, Command.upload_file)
        result = obj.upload_succeed(file_name2)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, 
                         (Command.release_file, file_name2))
        command, file_name3 = result.pop(0)
        self.assertEqual(command, Command.upload_file)
        result = obj.upload_succeed(file_name3)
        self.assertEqual(result, [(Command.release_file, file_name3), 
                                  ('_empty', None)]) 
        self.assertEqual(set([file_name, file_name2, file_name3]),
                         set(['file1', 'file2', 'file3']))
    
    def test_fail_once_one(self):
        obj = FilesUploadSubState()
        result = obj.start([('file1', 600000)])
        self.assertEqual(result, [(Command.upload_file, 'file1')])
        result = obj.upload_failed('file1')
        self.assertEqual(result, [(Command.upload_file, 'file1')]) 
        result = obj.upload_succeed('file1')
        self.assertEqual(result, [(Command.release_file, 'file1'), 
                                  ('_empty', None)]) 
                                  
    def test_fail_n_one(self):
        obj = FilesUploadSubState()
        result = obj.start([('file1', 600000)])
        self.assertEqual(result, [(Command.upload_file, 'file1')])
        result = obj.upload_failed('file1')
        self.assertEqual(result, [(Command.upload_file, 'file1')]) 
        result = obj.upload_failed('file1')
        self.assertEqual(result, [(Command.upload_file, 'file1')]) 
        result = obj.upload_failed('file1')
        self.assertEqual(result, [('_final_error', 'file1')]) 
        
    def test_fail_once_arr(self):
        obj = FilesUploadSubState()
        arr = [('file1', 600000), ('file2', 750000), ('file3', 1000000)]
        result = obj.start(arr)
        self.assertEqual(len(result), 1)
        command, file_name = result.pop()
        self.assertEqual(command, Command.upload_file)
        result = obj.upload_failed(file_name)
        self.assertEqual(len(result), 1)
        command, file_name2 = result.pop(0)
        self.assertEqual(command, Command.upload_file)
        result = obj.upload_failed(file_name2)
        self.assertEqual(len(result), 1)
        command, file_name3 = result.pop(0)
        self.assertEqual(command, Command.upload_file)
        self.assertEqual(set([file_name, file_name2, file_name3]),
                         set(['file1', 'file2', 'file3']))
        result = obj.upload_failed(file_name3)
        self.assertEqual(len(result), 1)
        command, file_name4 = result.pop()
        self.assertEqual(command, Command.upload_file)
        result = obj.upload_succeed(file_name4)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, 
                         (Command.release_file, file_name4))
        command, file_name5 = result.pop(0)
        self.assertEqual(command, Command.upload_file)
        result = obj.upload_succeed(file_name5)
        self.assertEqual(len(result), 2)
        release_cmd = result.pop(0)
        self.assertEqual(release_cmd, 
                         (Command.release_file, file_name5))
        command, file_name6 = result.pop(0)
        self.assertEqual(command, Command.upload_file)
        result = obj.upload_succeed(file_name6)
        self.assertEqual(result, [(Command.release_file, file_name6), 
                                  ('_empty', None)]) 
        self.assertEqual(set([file_name4, file_name5, file_name6]),
                         set(['file1', 'file2', 'file3']))
        
                                  
