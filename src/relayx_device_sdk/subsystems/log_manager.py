import asyncio
import datetime
import json
import sys
import traceback

from relayx_device_sdk.errors import ValidationError
from relayx_device_sdk.utils.subject_builder import SubjectBuilder


FLUSH_INTERVAL_SECONDS = 5.0
FLUSH_THRESHOLD = 15


def _validate_arg(arg):
    """Allow: str, int, float, bool, None, list, dict, datetime, BaseException."""
    if arg is None:
        return
    if isinstance(arg, bool):
        return
    if isinstance(arg, (str, int, float, list, dict, datetime.datetime)):
        return
    if isinstance(arg, BaseException):
        return
    raise ValidationError(
        f"device.log: unsupported argument type '{type(arg).__name__}'"
    )


def _format_arg(a):
    if a is None:
        return "None"
    if isinstance(a, bool):
        return str(a)
    if isinstance(a, (int, float)):
        return str(a)
    if isinstance(a, str):
        return a
    if isinstance(a, datetime.datetime):
        return a.isoformat()
    if isinstance(a, BaseException):
        head = f"{type(a).__name__}: {a}"
        if a.__traceback__ is not None:
            tb = "".join(
                traceback.format_exception(type(a), a, a.__traceback__)
            ).rstrip()
            return f"{head}\n{tb}"
        return head
    try:
        return json.dumps(a)
    except (TypeError, ValueError):
        return "[Unserializable]"


def _format_args(args):
    return " ".join(_format_arg(a) for a in args)


class LogManager:
    def __init__(self, transport, time_manager):
        self._transport = transport
        self._time = time_manager
        self._buffer = []
        self._timer_handle = None
        self._in_flight = set()
        self._last_timestamp = 0

    # ── Public API: sync, returns None ─────────────────────────────

    def info(self, *args):
        self._log("info", args)

    def warn(self, *args):
        self._log("warn", args)

    def error(self, *args):
        self._log("error", args)

    # ── Internals ───────────────────────────────────────────────────

    def _log(self, type_, args):
        for a in args:
            _validate_arg(a)

        # Console-equivalent forward with original args.
        # info → stdout; warn/error → stderr (matches console.* in JS).
        stream = sys.stdout if type_ == "info" else sys.stderr
        print(*args, file=stream)

        # Monotonic ms timestamp — Influx upserts on (measurement, tags, _field,
        # _time), so back-to-back logs in the same ms would overwrite each other.
        # Force strictly increasing timestamps within the device.
        now = self._time.now()
        ts = now if now > self._last_timestamp else self._last_timestamp + 1
        self._last_timestamp = ts

        self._buffer.append(
            {
                "type": type_,
                "timestamp": ts,
                "data": _format_args(args),
            }
        )

        if len(self._buffer) >= FLUSH_THRESHOLD:
            self._flush()
        elif self._timer_handle is None:
            self._schedule_timer()

    def _schedule_timer(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._timer_handle = loop.call_later(
            FLUSH_INTERVAL_SECONDS, self._on_timer
        )

    def _on_timer(self):
        self._timer_handle = None
        self._flush()

    def _flush(self):
        if self._timer_handle is not None:
            self._timer_handle.cancel()
            self._timer_handle = None

        if not self._buffer:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        entries = self._buffer
        self._buffer = []

        org_id = self._transport.get_org_id()
        env = self._transport.get_env()
        device_id = self._transport.get_device_id()

        for entry in entries:
            subject = SubjectBuilder.log(org_id, env, device_id, entry["type"])
            task = loop.create_task(self._publish_one(subject, entry))
            self._in_flight.add(task)
            task.add_done_callback(self._in_flight.discard)

    async def _publish_one(self, subject, entry):
        try:
            await self._transport.publish(subject, entry)
        except Exception as err:
            print(
                f"[device.log] publish failed: {err}",
                file=sys.stderr,
            )

    async def shutdown(self):
        self._flush()
        if self._in_flight:
            await asyncio.gather(*self._in_flight, return_exceptions=True)
