from unittest.mock import Mock, MagicMock


class GAuthMock:

    def __init__(self):
        self.access_token_expired = False
        #self.Refresh = () -> void <raise RefreshError>
        
        self.Refresh = MagicMock()
        
        self.Refresh.return_value = None

