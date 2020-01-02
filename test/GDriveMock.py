from unittest.mock import Mock, MagicMock
from GDriveFileMock import GDriveFileMock


class GDriveMock:

    def __init__(self, auth=None):
        self.auth = auth
        #self.CreateFile = (metadata: dict<opt>) -> GDriveFileMock
        #self.ListFile   = (param: dict<opt>) -> List[GDriveFileMock]
    
        self.CreateFile = MagicMock()
        self.ListFile = MagicMock()
    
        def create_file(*args, **kwargs):
            metadata = kwargs.get('metadata', {})
            return GDriveFileMock(metadata)
        
        self.CreateFile.side_effect = create_file
        self.ListFile.return_value = []
