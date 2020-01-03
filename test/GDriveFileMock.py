from unittest.mock import Mock, MagicMock
import random
import string


class GDriveFileMock:

    def __init__(self, dict_items = {}):
        self.__dict_items = dict_items
        #self.SetContentFile = (path: str<req>) -> void
        #self.Upload         = (opts: dict<opt>) -> void <raise ApiRequestError>
        
        self.SetContentFile = MagicMock()
        self.Upload = MagicMock()
        
        def create_id_if_none(*args, **kwargs):
            if 'id' not in self.__dict_items:
                letters = string.ascii_lowercase + string.digits
                id_val = ''.join(random.choice(letters) for i in range(8))
                self.__dict_items['id'] = id_val
        
        self.SetContentFile.return_value = None
        self.Upload.side_effect = create_id_if_none

    def __getitem__(self, key):
        if key not in self.__dict_items:
            raise RuntimeError('Unexpected key {}'.format(key))
        return self.__dict_items[key]

    def set_item(self, key, value):
        self.__dict_items[key] = value
        
    def has_item(self, key):
        return key in self.__dict_items


class ListFileResult:
    
    def __init__(self, files = []):
        #self.GetList = () -> [GDriveFileMock]
        self.GetList = MagicMock()
        self.GetList.return_value = files
