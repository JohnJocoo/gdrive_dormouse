from unittest.mock import Mock, MagicMock


class CommandCallbackMock:

    def __init__(self):
        self.called = MagicMock()
		
        self.called.return_value = None

    def __call__(self, cmd, data):
        self.called(cmd, data)
