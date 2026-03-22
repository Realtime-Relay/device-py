import pytest

from relayx_device_sdk.device import RelayDevice
from relayx_device_sdk.errors import ValidationError
from relayx_device_sdk.subsystems.time_manager import TimeManager
from relayx_device_sdk.subsystems.rpc_manager import RpcManager
from relayx_device_sdk.subsystems.command_manager import CommandManager
from relayx_device_sdk.subsystems.telemetry_manager import TelemetryManager
from relayx_device_sdk.subsystems.config_manager import ConfigManager
from relayx_device_sdk.subsystems.event_manager import EventManager
from relayx_device_sdk.subsystems.connection_manager import Connection
from tests.helpers.mock_transport import create_mock_transport


VALID_CONFIG = {
    "api_key": "test-jwt",
    "secret": "test-secret",
    "mode": "test",
}


class TestRelayDeviceConfig:
    def test_valid_config(self):
        transport = create_mock_transport()
        device = RelayDevice._create_for_test(VALID_CONFIG, transport)
        assert device is not None

    def test_missing_api_key(self):
        with pytest.raises(ValidationError):
            RelayDevice({"secret": "s", "mode": "test"})

    def test_empty_api_key(self):
        with pytest.raises(ValidationError):
            RelayDevice({"api_key": "", "secret": "s", "mode": "test"})

    def test_non_string_api_key(self):
        with pytest.raises(ValidationError):
            RelayDevice({"api_key": 123, "secret": "s", "mode": "test"})

    def test_missing_secret(self):
        with pytest.raises(ValidationError):
            RelayDevice({"api_key": "k", "mode": "test"})

    def test_empty_secret(self):
        with pytest.raises(ValidationError):
            RelayDevice({"api_key": "k", "secret": "", "mode": "test"})

    def test_missing_mode(self):
        with pytest.raises(ValidationError):
            RelayDevice({"api_key": "k", "secret": "s"})

    def test_invalid_mode(self):
        with pytest.raises(ValidationError):
            RelayDevice({"api_key": "k", "secret": "s", "mode": "staging"})

    def test_non_dict_config(self):
        with pytest.raises(ValidationError):
            RelayDevice("not a dict")


class TestRelayDeviceSubsystems:
    def test_subsystems_wired(self):
        transport = create_mock_transport()
        device = RelayDevice._create_for_test(VALID_CONFIG, transport)

        assert isinstance(device.time, TimeManager)
        assert isinstance(device.rpc, RpcManager)
        assert isinstance(device.command, CommandManager)
        assert isinstance(device.telemetry, TelemetryManager)
        assert isinstance(device.config, ConfigManager)
        assert isinstance(device.event, EventManager)
        assert isinstance(device.connection, Connection)


class TestRelayDeviceConnectDisconnect:
    async def test_connect_delegates_to_transport(self):
        transport = create_mock_transport()
        device = RelayDevice._create_for_test(VALID_CONFIG, transport)

        result = await device.connect()
        assert result is True
        assert transport.is_connected()

    async def test_disconnect_delegates_to_transport(self):
        transport = create_mock_transport()
        device = RelayDevice._create_for_test(VALID_CONFIG, transport)

        await device.connect()
        result = await device.disconnect()
        assert result is True
        assert not transport.is_connected()


class TestRelayDeviceConstants:
    def test_test_mode(self):
        assert RelayDevice.TEST_MODE == "test"

    def test_production_mode(self):
        assert RelayDevice.PRODUCTION_MODE == "production"


class TestRelayDeviceCreateForTest:
    def test_uses_mock_transport(self):
        transport = create_mock_transport()
        device = RelayDevice._create_for_test(VALID_CONFIG, transport)
        assert device._transport is transport
