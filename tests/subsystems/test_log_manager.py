import asyncio
import datetime

import pytest

from relayx_device_sdk.errors import ValidationError
from relayx_device_sdk.subsystems.log_manager import (
    LogManager,
    FLUSH_INTERVAL_SECONDS,
    FLUSH_THRESHOLD,
)
from tests.helpers.mock_transport import create_mock_transport


class FakeTime:
    def __init__(self, initial=1_000_000):
        self._t = initial

    def now(self):
        return self._t

    def advance(self, ms):
        self._t += ms


def make_transport():
    t = create_mock_transport()
    t._set_connected(True)
    return t


@pytest.fixture
def transport():
    return make_transport()


@pytest.fixture
def time_manager():
    return FakeTime()


@pytest.fixture
def log(transport, time_manager):
    return LogManager(transport, time_manager)


# ── Forwarding ─────────────────────────────────────────────────────


async def test_info_writes_to_stdout(log, capsys):
    log.info("hello", 42)
    captured = capsys.readouterr()
    assert "hello 42" in captured.out


async def test_warn_writes_to_stderr(log, capsys):
    log.warn("careful")
    captured = capsys.readouterr()
    assert "careful" in captured.err
    assert "careful" not in captured.out


async def test_error_writes_to_stderr(log, capsys):
    log.error("boom")
    captured = capsys.readouterr()
    assert "boom" in captured.err
    assert "boom" not in captured.out


# ── Validation ─────────────────────────────────────────────────────


async def test_accepts_string_number_bool_none(log):
    log.info("s", 1, 2.5, True, None)


async def test_accepts_dict_and_list(log):
    log.info({"a": 1}, [1, 2, 3])


async def test_accepts_datetime(log):
    log.info(datetime.datetime(2026, 4, 29, 12, 0, 0))


async def test_accepts_exception(log):
    log.info(ValueError("nope"))


async def test_rejects_function(log):
    with pytest.raises(ValidationError):
        log.info(lambda: None)


async def test_rejects_set(log):
    with pytest.raises(ValidationError):
        log.info({1, 2})


async def test_rejects_tuple(log):
    # Tuples are not in our allow-list (we want explicit list/dict).
    with pytest.raises(ValidationError):
        log.info((1, 2))


async def test_rejects_class_instance(log):
    class Foo:
        pass

    with pytest.raises(ValidationError):
        log.info(Foo())


async def test_rejects_when_any_arg_invalid(log):
    with pytest.raises(ValidationError):
        log.info("ok", 1, lambda: None)


async def test_validation_failure_does_not_print_or_buffer(log, transport, capsys):
    with pytest.raises(ValidationError):
        log.info(lambda: None)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    assert transport._get_published() == []


async def test_zero_args_allowed(log):
    log.info()


# ── Buffering ──────────────────────────────────────────────────────


async def test_does_not_publish_immediately(log, transport):
    log.info("a")
    await asyncio.sleep(0.05)  # let event loop settle
    assert transport._get_published() == []


async def test_flushes_after_timer(log, transport):
    log.info("a")
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    # gather any pending publish tasks
    await log.shutdown()
    assert len(transport._get_published()) == 1


async def test_threshold_flushes_immediately(log, transport):
    for i in range(FLUSH_THRESHOLD):
        log.info(f"m{i}")
    await asyncio.sleep(0.05)
    await log.shutdown()
    assert len(transport._get_published()) == FLUSH_THRESHOLD


async def test_threshold_flush_clears_timer(log, transport):
    for i in range(FLUSH_THRESHOLD):
        log.info(f"m{i}")
    await asyncio.sleep(0.05)
    before = len(transport._get_published())
    # Wait past timer; should not double-flush
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    assert len(transport._get_published()) == before


async def test_timer_is_debounced_not_reset(log, transport):
    """Timer measures from first entry into empty buffer; later entries do not reset."""
    log.info("a")  # starts timer at t=0
    await asyncio.sleep(2.0)
    log.info("b")  # does NOT reset
    # Total elapsed soon will be 5s+ since first log
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS - 2.0 + 0.2)
    await log.shutdown()
    assert len(transport._get_published()) == 2


async def test_empty_buffer_no_publish(log, transport):
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    assert transport._get_published() == []


# ── Subject + payload ──────────────────────────────────────────────


async def test_publishes_one_message_per_entry(log, transport):
    log.info("i")
    log.warn("w")
    log.error("e")
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    assert len(transport._get_published()) == 3


async def test_per_type_subjects(log, transport):
    log.info("i")
    log.warn("w")
    log.error("e")
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    subjects = {p["subject"] for p in transport._get_published()}
    assert "test-org.test.logs.test-device.info" in subjects
    assert "test-org.test.logs.test-device.warn" in subjects
    assert "test-org.test.logs.test-device.error" in subjects


async def test_payload_shape(log, transport, time_manager):
    log.info("hello", 42)
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    payload = transport._get_published()[0]["data"]
    assert payload["type"] == "info"
    assert payload["timestamp"] == 1_000_000
    assert payload["data"] == "hello 42"


async def test_timestamp_captured_at_log_time(log, transport, time_manager):
    log.info("a")
    time_manager.advance(1234)
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    assert transport._get_published()[0]["data"]["timestamp"] == 1_000_000


async def test_formats_dict_as_json(log, transport):
    log.info({"port": 8080})
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    assert transport._get_published()[0]["data"]["data"] == '{"port": 8080}'


async def test_formats_datetime_as_iso(log, transport):
    log.info(datetime.datetime(2026, 4, 29, 12, 0, 0))
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    assert (
        transport._get_published()[0]["data"]["data"] == "2026-04-29T12:00:00"
    )


async def test_formats_exception_with_name_and_message(log, transport):
    log.error(ValueError("boom"))
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    data = transport._get_published()[0]["data"]["data"]
    assert "ValueError" in data
    assert "boom" in data


async def test_formats_none(log, transport):
    log.info(None)
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    assert transport._get_published()[0]["data"]["data"] == "None"


async def test_zero_arg_call_publishes_empty_data(log, transport):
    log.info()
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()
    assert transport._get_published()[0]["data"]["data"] == ""


# ── Publish failure handling ───────────────────────────────────────


async def test_publish_failure_does_not_raise(log, transport, capsys):
    async def boom(*args, **kwargs):
        raise RuntimeError("transport boom")

    transport.publish = boom
    log.info("a")
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    await log.shutdown()  # must not raise
    captured = capsys.readouterr()
    assert "publish failed" in captured.err


# ── shutdown() ─────────────────────────────────────────────────────


async def test_shutdown_flushes_pending(log, transport):
    log.info("a")
    log.info("b")
    await log.shutdown()
    assert len(transport._get_published()) == 2


async def test_shutdown_clears_timer(log, transport):
    log.info("a")
    await log.shutdown()
    before = len(transport._get_published())
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)
    assert len(transport._get_published()) == before


async def test_shutdown_no_op_when_empty(log, transport):
    await log.shutdown()
    assert transport._get_published() == []


async def test_shutdown_awaits_in_flight(log, transport):
    release = asyncio.Event()

    async def slow_publish(subject, data):
        await release.wait()
        return True

    transport.publish = slow_publish
    log.info("a")
    # Trigger flush, which schedules slow_publish task
    await asyncio.sleep(FLUSH_INTERVAL_SECONDS + 0.1)

    settled = []

    async def run_shutdown():
        await log.shutdown()
        settled.append(True)

    shutdown_task = asyncio.create_task(run_shutdown())
    # Yield the event loop a couple of times; shutdown must still be waiting
    await asyncio.sleep(0.05)
    assert settled == []
    release.set()
    await shutdown_task
    assert settled == [True]


# ── SubjectBuilder.log ──────────────────────────────────────────────


def test_subject_builder_log_valid_types():
    from relayx_device_sdk.utils.subject_builder import SubjectBuilder

    assert (
        SubjectBuilder.log("o", "test", "d", "info") == "o.test.logs.d.info"
    )
    assert (
        SubjectBuilder.log("o", "test", "d", "warn") == "o.test.logs.d.warn"
    )
    assert (
        SubjectBuilder.log("o", "test", "d", "error") == "o.test.logs.d.error"
    )


def test_subject_builder_log_rejects_unknown_type():
    from relayx_device_sdk.utils.subject_builder import SubjectBuilder

    with pytest.raises(ValidationError):
        SubjectBuilder.log("o", "test", "d", "debug")
