from unittest.mock import MagicMock


class CommandCallbackMock(MagicMock):

    def __init__(self):
        self.called.return_value = None

    def __call__(self, cmd, data):
        self.called(cmd, data)
