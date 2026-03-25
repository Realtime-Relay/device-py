import traceback


class Logger:
    """Simple logger that only prints when mode is 'test'."""

    def __init__(self, env):
        self._enabled = (env == 'test')

    def error(self, msg, exc=None):
        if not self._enabled:
            return

        print(f'[relay-device-sdk] ERROR: {msg}')

        if exc:
            traceback.print_exception(type(exc), exc, exc.__traceback__)

    def warn(self, msg):
        if not self._enabled:
            return

        print(f'[relay-device-sdk] WARN: {msg}')

    def info(self, msg):
        if not self._enabled:
            return

        print(f'[relay-device-sdk] INFO: {msg}')

    def debug(self, msg):
        if not self._enabled:
            return

        print(f'[relay-device-sdk] DEBUG: {msg}')
