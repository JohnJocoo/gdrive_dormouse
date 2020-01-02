from unittest.mock import Mock, MagicMock


class GDriveFileMock:

    def __init__(self, dict_items = {}):
        self.__dict_items = dict_items
        #self.SetContentFile = (path: str<req>) -> void
        #self.Upload         = (opts: dict<opt>) -> void <raise ApiRequestError>
        
        self.SetContentFile = MagicMock()
        self.Upload = MagicMock()
        
        self.SetContentFile.return_value = None
        self.Upload.return_value = None

    def __getitem__(self, key):
        if key not in self.__dict_items:
            raise RuntimeError('Unexpected key {}'.format(key))
        return self.__dict_items[key]

    def set_item(self, key, value):
        self.__dict_items[key] = value
