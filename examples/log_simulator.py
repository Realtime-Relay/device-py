"""
Log Simulator
=============

Exercises every code path in device.log.{info,warn,error}:
  - all three levels with various arg shapes (str, int, float, bool, None,
    dict, list, datetime, BaseException)
  - bursts that trip the size-15 flush threshold
  - a quiet period that flushes via the 5s debounce timer
  - graceful shutdown that flushes any pending entries

Logs flush to:  <org_id>.<env>.logs.<device_id>.<info|warn|error>

Usage:
  RELAY_API_KEY=... RELAY_SECRET=... python examples/log_simulator.py
"""

import asyncio
import datetime
import json
import os

from relayx_device_sdk import RelayDevice

device = RelayDevice({
    "api_key": os.environ["RELAY_API_KEY"],
    "secret": os.environ["RELAY_SECRET"],
    "mode": os.environ.get("RELAY_MODE", "test"),
})

device.connection.listeners(
    lambda event: print(f"[connection] {event['type']}"),
)


async def main():
    connected = await device.connect()
    if not connected:
        print("Failed to connect")
        return
    print("Connected. Running log simulator...\n")

    # Phase 1: mixed-shape calls (8 entries, flushed by the 5s timer)
    print("[phase 1] mixed shapes — should flush via 5s timer")
    device.log.info("hello world")
    device.log.info("a number reading", 42)
    device.log.info("a boolean", True)
    device.log.info("none", None)
    device.log.info("a dict", {"port": 8080, "retries": 3})
    device.log.info("a list", [1, 2, 3])
    device.log.info("a datetime", datetime.datetime.now(datetime.timezone.utc))
    device.log.warn("careful — disk usage at 87%")
    await asyncio.sleep(6)

    # Phase 2: burst of 18 — first 15 flush immediately, trailing 3 via timer
    print("\n[phase 2] burst of 18 entries — first 15 flush immediately")
    for i in range(18):
        device.log.info("burst entry", i)
    await asyncio.sleep(6)

    # Phase 3: an actual exception
    print("\n[phase 3] log a BaseException")
    try:
        json.loads("{ not json")
    except Exception as err:
        device.log.error("parse failed", err)
    await asyncio.sleep(2)

    # Phase 4: validation failure (caller's mistake — does not crash)
    print("\n[phase 4] validation failure on bad arg")
    try:
        device.log.info("bad arg incoming", lambda: "i am a function")
    except Exception as err:
        print(f"caught: {type(err).__name__}: {err}")
    await asyncio.sleep(2)

    # Phase 5: graceful shutdown — flushes any pending entries
    print("\n[phase 5] disconnecting (flushes pending logs)")
    await device.disconnect()
    print("Disconnected.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
