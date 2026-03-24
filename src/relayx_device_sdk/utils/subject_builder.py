import re

from relayx_device_sdk.errors import ValidationError

TOKEN_REGEX = re.compile(r"^[A-Za-z0-9_-]+$")


def _validate_token(value: str, label: str) -> None:
    if not TOKEN_REGEX.match(value):
        raise ValidationError(
            f'{label} must match pattern ^[A-Za-z0-9_-]+$ (got "{value}")'
        )


class SubjectBuilder:
    @staticmethod
    def rpc(org_id: str, env: str, device_id: str, name: str) -> str:
        _validate_token(name, "name")
        return f"{org_id}.{env}.command.rpc.{device_id}.{name}"

    @staticmethod
    def command(org_id: str, env: str, device_id: str, name: str) -> str:
        _validate_token(name, "name")
        return f"{org_id}.{env}.command.queue.{device_id}.{name}"

    @staticmethod
    def telemetry(org_id: str, env: str, device_id: str, metric: str) -> str:
        _validate_token(metric, "metric")
        return f"{org_id}.{env}.telemetry.{device_id}.{metric}"

    @staticmethod
    def config_get(org_id: str) -> str:
        return f"api.iot.devices.{org_id}.sdk.config.get"

    @staticmethod
    def config_set(org_id: str) -> str:
        return f"api.iot.devices.{org_id}.sdk.config.update"

    @staticmethod
    def schema_get(org_id: str) -> str:
        return f"api.iot.devices.{org_id}.sdk.schema.get"

    @staticmethod
    def event(org_id: str, env: str, device_id: str, event_name: str) -> str:
        _validate_token(event_name, "eventName")
        return f"{org_id}.{env}.events.{device_id}.{event_name}"
