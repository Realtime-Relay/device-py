from relayx_device_sdk.subsystems.event_manager import EventManager
from tests.helpers.mock_transport import create_mock_transport


def make_transport(**kwargs):
    t = create_mock_transport(**kwargs)
    t._set_connected(True)
    return t


class TestEventSend:
    async def test_publishes_to_correct_subject(self):
        transport = make_transport()
        events = EventManager(transport)

        await events.send("door-opened", {"door": "front"})

        published = transport._get_published()
        assert len(published) == 1
        assert published[0]["subject"] == "test-org.test.event.test-device.door-opened"

    async def test_payload_passed_through(self):
        transport = make_transport()
        events = EventManager(transport)

        data = {"door": "front", "timestamp": 123}
        await events.send("door-opened", data)

        published = transport._get_published()
        assert published[0]["data"] == data

    async def test_returns_true_when_connected(self):
        transport = make_transport()
        events = EventManager(transport)

        result = await events.send("door-opened", {"door": "front"})
        assert result is True

    async def test_returns_false_when_disconnected(self):
        transport = make_transport()
        transport._set_connected(False)
        events = EventManager(transport)

        result = await events.send("door-opened", {"door": "front"})
        assert result is False
