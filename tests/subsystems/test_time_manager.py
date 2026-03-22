import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from relayx_device_sdk.errors import NotConnectedError
from relayx_device_sdk.subsystems.time_manager import TimeManager
from tests.helpers.mock_transport import create_mock_transport


def make_transport():
    t = create_mock_transport()
    t._set_connected(True)
    return t


class TestTimeInit:
    async def test_raises_when_not_connected(self):
        transport = create_mock_transport()
        tm = TimeManager(transport)

        with pytest.raises(NotConnectedError):
            await tm.init()

    async def test_calculates_offset(self):
        transport = make_transport()
        tm = TimeManager(transport)

        class FakeResponse:
            tx_time = time.time() + 0.5  # server 500ms ahead

        with patch("relayx_device_sdk.subsystems.time_manager.ntplib") as mock_ntplib:
            mock_client = MagicMock()
            mock_client.request.return_value = FakeResponse()
            mock_ntplib.NTPClient.return_value = mock_client

            await tm.init()

        now = tm.now()
        expected = int(time.time() * 1000 + 500)
        assert abs(now - expected) < 100  # within 100ms tolerance


class TestTimeNow:
    def test_returns_int(self):
        transport = make_transport()
        tm = TimeManager(transport)
        assert isinstance(tm.now(), int)

    def test_returns_reasonable_timestamp(self):
        transport = make_transport()
        tm = TimeManager(transport)
        now = tm.now()
        # Should be within 1 second of current time (offset is 0 by default)
        assert abs(now - int(time.time() * 1000)) < 1000


class TestTimeToDate:
    def test_converts_ms_to_datetime(self):
        transport = make_transport()
        tm = TimeManager(transport)

        ts = 1700000000000  # Nov 14, 2023
        dt = tm.to_date(ts)

        assert isinstance(dt, datetime)
        assert dt.year == 2023
        assert dt.month == 11

    def test_respects_timezone(self):
        transport = make_transport()
        tm = TimeManager(transport)
        tm.set_timezone("US/Eastern")

        ts = 1700000000000
        dt = tm.to_date(ts)

        assert str(dt.tzinfo) == "US/Eastern"


class TestTimeToTimestamp:
    def test_converts_datetime_to_ms(self):
        transport = make_transport()
        tm = TimeManager(transport)

        dt = datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)
        ts = tm.to_timestamp(dt)

        assert isinstance(ts, int)
        assert ts == 1700000000000


class TestTimeSetTimezone:
    def test_stores_timezone(self):
        transport = make_transport()
        tm = TimeManager(transport)

        tm.set_timezone("America/New_York")
        assert tm._timezone == "America/New_York"


class TestTimeSyncOnConnect:
    async def test_syncs_on_connect_status(self):
        transport = make_transport()
        tm = TimeManager(transport)

        class FakeResponse:
            tx_time = time.time()

        with patch("relayx_device_sdk.subsystems.time_manager.ntplib") as mock_ntplib:
            mock_client = MagicMock()
            mock_client.request.return_value = FakeResponse()
            mock_ntplib.NTPClient.return_value = mock_client

            from relayx_device_sdk.transport import TransportStatus
            transport._emit_status({"type": TransportStatus.CONNECTED})

            # Give the async task a chance to run
            import asyncio
            await asyncio.sleep(0.1)

            assert mock_client.request.called
