class Connection:
    def __init__(self, transport):
        self._transport = transport

    def listeners(self, callback):
        self._transport.on_status(callback)
