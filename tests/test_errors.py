from relayx_device_sdk.errors import (
    ValidationError,
    DuplicateListenerError,
    NotConnectedError,
    TimeoutError,
)


class TestValidationError:
    def test_message(self):
        err = ValidationError("invalid input")
        assert str(err) == "invalid input"

    def test_is_exception(self):
        assert issubclass(ValidationError, Exception)


class TestDuplicateListenerError:
    def test_message_format(self):
        err = DuplicateListenerError("my-listener")
        assert str(err) == 'Listener "my-listener" is already registered'

    def test_name_attribute(self):
        err = DuplicateListenerError("foo")
        assert err.name == "foo"

    def test_is_exception(self):
        assert issubclass(DuplicateListenerError, Exception)


class TestNotConnectedError:
    def test_message(self):
        err = NotConnectedError()
        assert str(err) == "Not connected to the server"

    def test_is_exception(self):
        assert issubclass(NotConnectedError, Exception)


class TestTimeoutError:
    def test_message_with_subject(self):
        err = TimeoutError("my.subject")
        assert str(err) == 'Request timed out on subject "my.subject"'
        assert err.subject == "my.subject"

    def test_message_without_subject(self):
        err = TimeoutError()
        assert str(err) == "Request timed out"
        assert err.subject is None

    def test_is_exception(self):
        assert issubclass(TimeoutError, Exception)
