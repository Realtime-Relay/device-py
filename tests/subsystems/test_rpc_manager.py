import json
import pytest

from relayx_device_sdk.errors import DuplicateListenerError, ValidationError
from relayx_device_sdk.subsystems.rpc_manager import RpcManager, RpcRequest
from tests.helpers.mock_transport import create_mock_transport


def make_transport(**kwargs):
    t = create_mock_transport(**kwargs)
    t._set_connected(True)
    return t


class TestRpcListen:
    async def test_subscribes_to_correct_subject(self):
        transport = make_transport()
        rpc = RpcManager(transport)

        await rpc.listen("reboot", lambda req: None)

        subs = transport._get_subscriptions()
        assert "test-org.test.command.rpc.test-device.reboot" in subs

    async def test_raises_on_non_callable(self):
        transport = make_transport()
        rpc = RpcManager(transport)

        with pytest.raises(ValidationError):
            await rpc.listen("reboot", "not a function")

    async def test_raises_on_duplicate(self):
        transport = make_transport()
        rpc = RpcManager(transport)

        await rpc.listen("reboot", lambda req: None)

        with pytest.raises(DuplicateListenerError):
            await rpc.listen("reboot", lambda req: None)

    async def test_callback_receives_rpc_request(self):
        transport = make_transport()
        rpc = RpcManager(transport)

        received = []

        async def handler(req):
            received.append(req)

        await rpc.listen("reboot", handler)

        subject = "test-org.test.command.rpc.test-device.reboot"
        sub = transport._get_subscriptions()[subject]

        class FakeMsg:
            async def respond(self, data):
                self.responded_with = data

        fake_msg = FakeMsg()
        await sub.callback({"action": "reboot"}, fake_msg)

        assert len(received) == 1
        assert isinstance(received[0], RpcRequest)
        assert received[0].payload == {"action": "reboot"}


class TestRpcOff:
    async def test_removes_listener(self):
        transport = make_transport()
        rpc = RpcManager(transport)

        await rpc.listen("reboot", lambda req: None)
        result = await rpc.off("reboot")

        assert result is True
        subs = transport._get_subscriptions()
        assert "test-org.test.command.rpc.test-device.reboot" not in subs

    async def test_returns_false_for_missing(self):
        transport = make_transport()
        rpc = RpcManager(transport)

        result = await rpc.off("nonexistent")
        assert result is False

    async def test_can_re_register_after_off(self):
        transport = make_transport()
        rpc = RpcManager(transport)

        await rpc.listen("reboot", lambda req: None)
        await rpc.off("reboot")
        await rpc.listen("reboot", lambda req: None)

        subs = transport._get_subscriptions()
        assert "test-org.test.command.rpc.test-device.reboot" in subs


class TestRpcRequest:
    async def test_respond_sends_ok(self):
        class FakeMsg:
            async def respond(self, data):
                self.responded_with = data

        msg = FakeMsg()
        req = RpcRequest({"foo": "bar"}, msg)

        await req.respond({"result": 42})

        response = json.loads(msg.responded_with.decode("utf-8"))
        assert response == {"status": "ok", "data": {"result": 42}}

    async def test_error_sends_error(self):
        class FakeMsg:
            async def respond(self, data):
                self.responded_with = data

        msg = FakeMsg()
        req = RpcRequest({"foo": "bar"}, msg)

        await req.error({"message": "failed"})

        response = json.loads(msg.responded_with.decode("utf-8"))
        assert response == {"status": "error", "data": {"message": "failed"}}

    def test_payload_exposed(self):
        req = RpcRequest({"key": "value"}, None)
        assert req.payload == {"key": "value"}
