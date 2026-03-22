import pytest

from relayx_device_sdk.errors import ValidationError
from relayx_device_sdk.utils.subject_builder import SubjectBuilder


class TestSubjectBuilderRpc:
    def test_builds_correct_subject(self):
        result = SubjectBuilder.rpc("org1", "test", "dev1", "reboot")
        assert result == "org1.test.command.rpc.dev1.reboot"

    def test_validates_name(self):
        with pytest.raises(ValidationError):
            SubjectBuilder.rpc("org1", "test", "dev1", "bad.name")

    def test_allows_hyphens_and_underscores(self):
        result = SubjectBuilder.rpc("org1", "test", "dev1", "my-command_1")
        assert result == "org1.test.command.rpc.dev1.my-command_1"

    def test_rejects_spaces(self):
        with pytest.raises(ValidationError):
            SubjectBuilder.rpc("org1", "test", "dev1", "bad name")

    def test_rejects_special_chars(self):
        with pytest.raises(ValidationError):
            SubjectBuilder.rpc("org1", "test", "dev1", "bad!name")


class TestSubjectBuilderCommand:
    def test_builds_correct_subject(self):
        result = SubjectBuilder.command("org1", "test", "dev1", "update")
        assert result == "org1.test.command.queue.dev1.update"

    def test_validates_name(self):
        with pytest.raises(ValidationError):
            SubjectBuilder.command("org1", "test", "dev1", "bad.name")


class TestSubjectBuilderTelemetry:
    def test_builds_correct_subject(self):
        result = SubjectBuilder.telemetry("org1", "test", "dev1", "temperature")
        assert result == "org1.test.telemetry.dev1.temperature"

    def test_validates_metric(self):
        with pytest.raises(ValidationError):
            SubjectBuilder.telemetry("org1", "test", "dev1", "bad.metric")


class TestSubjectBuilderConfig:
    def test_config_get(self):
        result = SubjectBuilder.config_get("org1")
        assert result == "api.iot.devices.org1.sdk.config.get"

    def test_config_set(self):
        result = SubjectBuilder.config_set("org1")
        assert result == "api.iot.devices.org1.sdk.config.update"


class TestSubjectBuilderSchema:
    def test_schema_get(self):
        result = SubjectBuilder.schema_get("org1")
        assert result == "api.iot.devices.org1.sdk.schema.get"


class TestSubjectBuilderEvent:
    def test_builds_correct_subject(self):
        result = SubjectBuilder.event("org1", "test", "dev1", "door-opened")
        assert result == "org1.test.event.dev1.door-opened"

    def test_validates_event_name(self):
        with pytest.raises(ValidationError):
            SubjectBuilder.event("org1", "test", "dev1", "bad.event")

    def test_rejects_empty_string(self):
        with pytest.raises(ValidationError):
            SubjectBuilder.event("org1", "test", "dev1", "")
