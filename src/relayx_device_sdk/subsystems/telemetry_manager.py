from relayx_device_sdk.errors import ValidationError
from relayx_device_sdk.utils.subject_builder import SubjectBuilder


def _get_reading_type(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (dict, list)):
        return "json"
    return None


class TelemetryManager:
    def __init__(self, transport, time_manager):
        self._transport = transport
        self._time = time_manager

    async def publish(self, metric: str, reading=None) -> bool:
        schema = self._transport.get_schema()

        if schema is not None:
            if metric not in schema:
                raise ValidationError(
                    f'Metric "{metric}" is not defined in the device schema'
                )

            if reading is not None:
                expected_type = schema[metric].get('type') if isinstance(schema[metric], dict) else schema[metric]
                actual_type = _get_reading_type(reading)

                if actual_type != expected_type:
                    raise ValidationError(
                        f'Reading type mismatch for metric "{metric}": '
                        f'expected {expected_type}, got {actual_type}'
                    )

        subject = SubjectBuilder.telemetry(
            self._transport.get_org_id(),
            self._transport.get_env(),
            self._transport.get_device_id(),
            metric,
        )

        payload = {
            "value": reading,
            "timestamp": self._time.now(),
        }

        return await self._transport.publish(subject, payload)
