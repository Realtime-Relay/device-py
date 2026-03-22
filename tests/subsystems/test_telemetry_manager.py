import pytest

from relayx_device_sdk.errors import ValidationError
from relayx_device_sdk.subsystems.telemetry_manager import TelemetryManager
from tests.helpers.mock_transport import create_mock_transport


class MockTime:
    def now(self):
        return 1700000000000


def make_transport(schema=None, **kwargs):
    t = create_mock_transport(overrides={"schema": schema, **kwargs})
    t._set_connected(True)
    return t


class TestTelemetryPublish:
    async def test_publishes_to_correct_subject(self):
        transport = make_transport()
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("temperature", 25.5)

        published = transport._get_published()
        assert len(published) == 1
        assert published[0]["subject"] == "test-org.test.telemetry.test-device.temperature"

    async def test_payload_structure(self):
        transport = make_transport()
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("temperature", 25.5)

        published = transport._get_published()
        assert published[0]["data"] == {
            "value": 25.5,
            "timestamp": 1700000000000,
        }

    async def test_returns_true_when_connected(self):
        transport = make_transport()
        telemetry = TelemetryManager(transport, MockTime())

        result = await telemetry.publish("temperature", 25.5)
        assert result is True

    async def test_returns_false_when_disconnected(self):
        transport = make_transport()
        transport._set_connected(False)
        telemetry = TelemetryManager(transport, MockTime())

        result = await telemetry.publish("temperature", 25.5)
        assert result is False


class TestTelemetrySchemaValidation:
    async def test_rejects_unknown_metric(self):
        schema = {"temperature": "number", "humidity": "number"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        with pytest.raises(ValidationError, match="not defined"):
            await telemetry.publish("pressure", 1013)

    async def test_rejects_type_mismatch_number(self):
        schema = {"temperature": "number"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        with pytest.raises(ValidationError, match="type mismatch"):
            await telemetry.publish("temperature", "not a number")

    async def test_rejects_type_mismatch_string(self):
        schema = {"status": "string"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        with pytest.raises(ValidationError, match="type mismatch"):
            await telemetry.publish("status", 42)

    async def test_rejects_type_mismatch_boolean(self):
        schema = {"active": "boolean"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        with pytest.raises(ValidationError, match="type mismatch"):
            await telemetry.publish("active", "true")

    async def test_rejects_type_mismatch_json(self):
        schema = {"metadata": "json"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        with pytest.raises(ValidationError, match="type mismatch"):
            await telemetry.publish("metadata", 42)

    async def test_allows_correct_number(self):
        schema = {"temperature": "number"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("temperature", 25.5)
        assert len(transport._get_published()) == 1

    async def test_allows_correct_string(self):
        schema = {"status": "string"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("status", "online")
        assert len(transport._get_published()) == 1

    async def test_allows_correct_boolean(self):
        schema = {"active": "boolean"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("active", True)
        assert len(transport._get_published()) == 1

    async def test_allows_correct_json_dict(self):
        schema = {"metadata": "json"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("metadata", {"key": "value"})
        assert len(transport._get_published()) == 1

    async def test_allows_correct_json_list(self):
        schema = {"metadata": "json"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("metadata", [1, 2, 3])
        assert len(transport._get_published()) == 1

    async def test_null_reading_skips_type_check(self):
        schema = {"temperature": "number"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("temperature", None)
        assert len(transport._get_published()) == 1

    async def test_no_schema_allows_anything(self):
        transport = make_transport(schema=None)
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("anything", "any value")
        assert len(transport._get_published()) == 1

    async def test_boolean_not_treated_as_number(self):
        schema = {"temperature": "number"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        with pytest.raises(ValidationError, match="type mismatch"):
            await telemetry.publish("temperature", True)

    async def test_int_treated_as_number(self):
        schema = {"count": "number"}
        transport = make_transport(schema=schema)
        telemetry = TelemetryManager(transport, MockTime())

        await telemetry.publish("count", 42)
        assert len(transport._get_published()) == 1
