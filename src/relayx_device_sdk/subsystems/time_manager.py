import asyncio
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import ntplib

from relayx_device_sdk.errors import NotConnectedError
from relayx_device_sdk.transport import TransportStatus

THREE_HOURS_MS = 3 * 60 * 60 * 1000


class TimeManager:
    def __init__(self, transport):
        self._transport = transport
        self._offset_ms: float = 0
        self._last_sync_at: float = 0
        self._timezone: str | None = None

        self._transport.on_status(self._on_status)

    def _on_status(self, event: dict):
        event_type = event.get("type")
        if event_type in (TransportStatus.CONNECTED, TransportStatus.RECONNECTED):
            if self._is_sync_stale():
                asyncio.create_task(self.init())

    async def init(self) -> None:
        if not self._transport.is_connected():
            raise NotConnectedError()

        loop = asyncio.get_running_loop()
        client = ntplib.NTPClient()
        response = await loop.run_in_executor(
            None, lambda: client.request("time.google.com", version=3)
        )

        ntp_time_ms = response.tx_time * 1000
        local_ms = time.time() * 1000
        self._offset_ms = ntp_time_ms - local_ms
        self._last_sync_at = time.time() * 1000

    def now(self) -> int:
        return int(time.time() * 1000 + self._offset_ms)

    def to_date(self, timestamp: int) -> datetime:
        dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        if self._timezone:
            dt = dt.astimezone(ZoneInfo(self._timezone))
        return dt

    def to_timestamp(self, dt: datetime) -> int:
        return int(dt.timestamp() * 1000)

    def set_timezone(self, tz: str) -> None:
        self._timezone = tz

    def _is_sync_stale(self) -> bool:
        if self._last_sync_at == 0:
            return True
        return (time.time() * 1000 - self._last_sync_at) >= THREE_HOURS_MS
