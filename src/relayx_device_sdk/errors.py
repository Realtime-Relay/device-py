class ValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class DuplicateListenerError(Exception):
    def __init__(self, name: str):
        super().__init__(f'Listener "{name}" is already registered')
        self.name = name


class NotConnectedError(Exception):
    def __init__(self):
        super().__init__("Not connected to the server")


class TimeoutError(Exception):
    def __init__(self, subject: str | None = None):
        if subject:
            super().__init__(f'Request timed out on subject "{subject}"')
        else:
            super().__init__("Request timed out")
        self.subject = subject
