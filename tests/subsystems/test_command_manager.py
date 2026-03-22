import pytest

from relayx_device_sdk.errors import DuplicateListenerError, ValidationError
from relayx_device_sdk.subsystems.command_manager import CommandManager, CommandMessage
from tests.helpers.mock_transport import create_mock_transport


def make_transport(**kwargs):
    t = create_mock_transport(**kwargs)
    t._set_connected(True)
    return t


class TestCommandListen:
    async def test_subscribes_to_correct_subject(self):
        transport = make_transport()
        cmd = CommandManager(transport)

        await cmd.listen("update-firmware", lambda msg: None)

        subs = transport._get_subscriptions()
        assert "test-org.test.command.queue.test-device.update-firmware" in subs

    async def test_raises_on_non_callable(self):
        transport = make_transport()
        cmd = CommandManager(transport)

        with pytest.raises(ValidationError):
            await cmd.listen("update", "not callable")

    async def test_raises_on_duplicate(self):
        transport = make_transport()
        cmd = CommandManager(transport)

        await cmd.listen("update", lambda msg: None)

        with pytest.raises(DuplicateListenerError):
            await cmd.listen("update", lambda msg: None)

    async def test_callback_receives_command_message(self):
        transport = make_transport()
        cmd = CommandManager(transport)

        received = []

        def handler(msg):
            received.append(msg)

        await cmd.listen("update", handler)

        subject = "test-org.test.command.queue.test-device.update"
        transport._simulate_js_message(subject, {"version": "2.0"})

        assert len(received) == 1
        assert isinstance(received[0], CommandMessage)
        assert received[0].payload == {"version": "2.0"}


class TestCommandOff:
    async def test_removes_listener(self):
        transport = make_transport()
        cmd = CommandManager(transport)

        await cmd.listen("update", lambda msg: None)
        result = await cmd.off("update")

        assert result is True

    async def test_returns_false_for_missing(self):
        transport = make_transport()
        cmd = CommandManager(transport)

        result = await cmd.off("nonexistent")
        assert result is False

    async def test_can_re_register_after_off(self):
        transport = make_transport()
        cmd = CommandManager(transport)

        await cmd.listen("update", lambda msg: None)
        await cmd.off("update")
        await cmd.listen("update", lambda msg: None)

        subs = transport._get_subscriptions()
        assert "test-org.test.command.queue.test-device.update" in subs


class TestCommandMessage:
    def test_payload_exposed(self):
        msg = CommandMessage({"key": "value"})
        assert msg.payload == {"key": "value"}
