from relayx_device_sdk.errors import ValidationError
from relayx_device_sdk.transport import NatsTransport
from relayx_device_sdk.subsystems.time_manager import TimeManager
from relayx_device_sdk.subsystems.rpc_manager import RpcManager
from relayx_device_sdk.subsystems.command_manager import CommandManager
from relayx_device_sdk.subsystems.telemetry_manager import TelemetryManager
from relayx_device_sdk.subsystems.config_manager import ConfigManager
from relayx_device_sdk.subsystems.event_manager import EventManager
from relayx_device_sdk.subsystems.log_manager import LogManager
from relayx_device_sdk.subsystems.connection_manager import Connection


class RelayDevice:
    TEST_MODE = "test"
    PRODUCTION_MODE = "production"
    _VALID_MODES = (TEST_MODE, PRODUCTION_MODE)

    def __init__(self, config: dict, _test_transport=None):
        self._validate_config(config)
        self._config = config

        self._transport = _test_transport or NatsTransport(config)

        self._init_subsystems()

    def _init_subsystems(self):
        self.time = TimeManager(self._transport)
        self.rpc = RpcManager(self._transport)
        self.command = CommandManager(self._transport)
        self.telemetry = TelemetryManager(self._transport, self.time)
        self.config = ConfigManager(self._transport)
        self.event = EventManager(self._transport)
        self.log = LogManager(self._transport, self.time)
        self.connection = Connection(self._transport)

    @staticmethod
    def _create_for_test(config: dict, mock_transport):
        return RelayDevice(config, _test_transport=mock_transport)

    async def connect(self) -> bool:
        return await self._transport.connect()

    async def disconnect(self) -> bool:
        await self.log.shutdown()
        return await self._transport.disconnect()

    @staticmethod
    def _validate_config(config: dict):
        if not isinstance(config, dict):
            raise ValidationError("config must be a dict")

        api_key = config.get("api_key")
        if not api_key or not isinstance(api_key, str):
            raise ValidationError("api_key is required and must be a non-empty string")

        secret = config.get("secret")
        if not secret or not isinstance(secret, str):
            raise ValidationError("secret is required and must be a non-empty string")

        mode = config.get("mode")
        if mode not in RelayDevice._VALID_MODES:
            raise ValidationError(
                f"mode must be '{RelayDevice.TEST_MODE}' or '{RelayDevice.PRODUCTION_MODE}'"
            )
