import pytest

from relayx_device_sdk.subsystems.config_manager import ConfigManager
from tests.helpers.mock_transport import create_mock_transport


def make_transport(request_handler=None):
    t = create_mock_transport(overrides={"request_handler": request_handler})
    t._set_connected(True)
    return t


class TestConfigGet:
    async def test_returns_config_on_success(self):
        def handler(subject, data, opts):
            return {
                "status": "DEVICE_CONFIG_FETCH_SUCCESS",
                "data": {"config": {"interval": 30, "debug": True}},
            }

        transport = make_transport(request_handler=handler)
        cfg = ConfigManager(transport)

        result = await cfg.get()
        assert result == {"interval": 30, "debug": True}

    async def test_returns_none_on_failure(self):
        def handler(subject, data, opts):
            return {"status": "DEVICE_CONFIG_FETCH_FAILURE", "data": {}}

        transport = make_transport(request_handler=handler)
        cfg = ConfigManager(transport)

        result = await cfg.get()
        assert result is None

    async def test_sends_correct_subject(self):
        transport = make_transport()
        cfg = ConfigManager(transport)

        await cfg.get()

        requests = transport._get_requests()
        assert len(requests) == 1
        assert requests[0]["subject"] == "api.iot.devices.test-org.sdk.config.get"

    async def test_sends_device_id_in_payload(self):
        transport = make_transport()
        cfg = ConfigManager(transport)

        await cfg.get()

        requests = transport._get_requests()
        assert requests[0]["data"] == {"id": "test-device"}


class TestConfigSet:
    async def test_returns_true_on_success(self):
        def handler(subject, data, opts):
            return {"status": "DEVICE_CONFIG_UPDATE_SUCCESS", "data": {}}

        transport = make_transport(request_handler=handler)
        cfg = ConfigManager(transport)

        result = await cfg.set({"interval": 60})
        assert result is True

    async def test_returns_false_on_failure(self):
        def handler(subject, data, opts):
            return {"status": "DEVICE_CONFIG_UPDATE_FAILURE", "data": {}}

        transport = make_transport(request_handler=handler)
        cfg = ConfigManager(transport)

        result = await cfg.set({"interval": 60})
        assert result is False

    async def test_sends_correct_subject(self):
        transport = make_transport()
        cfg = ConfigManager(transport)

        await cfg.set({"interval": 60})

        requests = transport._get_requests()
        assert requests[0]["subject"] == "api.iot.devices.test-org.sdk.config.update"

    async def test_sends_correct_payload(self):
        transport = make_transport()
        cfg = ConfigManager(transport)

        await cfg.set({"interval": 60})

        requests = transport._get_requests()
        assert requests[0]["data"] == {
            "id": "test-device",
            "config": {"interval": 60},
        }
