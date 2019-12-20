from unittest.mock import MagicMock


class GAuthMock(MagicMock):

    def __init__(self):
        self.access_token_expired = False
        #self.Refresh = () -> void <raise RefreshError>
        
        self.Refresh.return_value = None

