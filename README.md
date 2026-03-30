# RelayX Device SDK for Python

Official Python SDK for connecting IoT devices to the RelayX platform.

> **[View Full Documentation →](https://docs.relay-x.io/device-sdk/overview)**

## Installation

```bash
pip install relayx_device_sdk
```

## Quick Start

```python
import asyncio
from relayx_device_sdk import RelayDevice

device = RelayDevice({
    "api_key": "<YOUR_API_KEY>",
    "secret": "<YOUR_SECRET>",
    "mode": "production",  # or "test"
})

async def main():
    await device.connect()

    # Publish telemetry
    await device.telemetry.publish("temperature", 22.5)

    # Listen for RPC calls
    async def on_reboot(req):
        print("Reboot requested:", req.payload)
        await req.respond({"status": "rebooting"})

    await device.rpc.listen("reboot", on_reboot)

    # Listen for commands
    def on_firmware_update(msg):
        print("Firmware update:", msg.payload)

    await device.command.listen("firmware_update", on_firmware_update)

    # Disconnect when done
    await device.disconnect()

asyncio.run(main())
```

## Configuration

```python
device = RelayDevice({
    "api_key": "<YOUR_API_KEY>",   # JWT issued by RelayX
    "secret": "<YOUR_SECRET>",      # NKEY seed
    "mode": "production",           # "production" | "test"
})
```

The `api_key` is a NATS JWT that encodes your `orgId` and `deviceId`. These are extracted automatically on connect.

## Functionality

### Connection

```python
await device.connect()     # returns True on success, False if already connected or failed
await device.disconnect()  # drains NATS connection, cleans up consumers

# Listen for connection status changes
device.connection.listeners(lambda event: print("Status:", event["type"]))
# event["type"]: "connected" | "disconnected" | "reconnecting" | "reconnected" | "auth_failed"
```

### Telemetry

Fire-and-forget sensor data publishing. Readings are validated against the device schema fetched on connect.

```python
await device.telemetry.publish("temperature", 22.5)          # number
await device.telemetry.publish("status", "online")            # string
await device.telemetry.publish("active", True)                # boolean
await device.telemetry.publish("metadata", {"fw": "1.2"})    # json
```

Each message is published with a server-synced timestamp.

**Schema validation**: On connect, the SDK fetches the device schema from the server. If a schema exists, `publish()` will throw a `ValidationError` if the metric name is not in the schema or the reading type does not match.

### Remote Procedure Calls (RPC)

Register handlers for incoming RPC calls.

```python
# Register a handler
async def on_get_status(req):
    print("Payload:", req.payload)

    # Respond with success
    await req.respond({"uptime": 12345})

    # Or respond with error
    # await req.error({"code": "UNAVAILABLE", "message": "Device busy"})

await device.rpc.listen("get_status", on_get_status)

# Unregister
await device.rpc.off("get_status")
```

Duplicate listeners for the same name throw `DuplicateListenerError`.

### Commands

One-way commands delivered for long running tasks that do not require a status update.

```python
def on_firmware_update(msg):
    print("Command:", msg.payload)

    # Process based on data...

await device.command.listen("firmware_update", on_firmware_update)

await device.command.off("firmware_update")
```

### Config

Get and set device configuration via request/reply.

```python
# Fetch current config
config = await device.config.get()
print(config)

# Update config
success = await device.config.set({"interval": 10000, "name": "sensor-1"})
```

### Events

Fire-and-forget event publishing of events (fault codes, etc).

```python
await device.event.send("door_opened", {"door_id": "front", "timestamp": device.time.now()})
```

### Time

NTP-synchronized clock. Syncs with `time.google.com` on connect and every 3 hours. Auto-resyncs on reconnect if stale.

```python
# Initialize (called automatically on connect)
await device.time.init()

# Get current server-corrected timestamp (ms)
now = device.time.now()

# Convert SDK timestamp to datetime
dt = device.time.to_date(now)

# Convert datetime to SDK timestamp
ts = device.time.to_timestamp(datetime.now())

# Set timezone for display
device.time.set_timezone("America/New_York")
```

## Error Handling

The SDK exports four error types:

```python
from relayx_device_sdk import (
    NotConnectedError,       # Operation attempted while disconnected
    DuplicateListenerError,  # rpc.listen() or command.listen() called twice for same name
    ValidationError,         # Invalid arguments or schema mismatch
    TimeoutError,            # Request/reply timed out
)
```

## Offline Behavior

- **Telemetry & Events** (`publish`): Messages are buffered in memory while disconnected and flushed automatically on reconnect.
- **RPC & Commands** (`listen`): Throw `NotConnectedError` if transport is disconnected.
- **Config** (`get`/`set`): Throw `NotConnectedError` if transport is disconnected.

## Testing

```bash
pytest
```

The SDK is designed for full unit testability. All subsystems accept a transport dependency that can be mocked:

```python
from relayx_device_sdk import RelayDevice

mock_transport = ...  # mock methods
device = RelayDevice._create_for_test(
    {"api_key": "test", "secret": "test", "mode": "test"},
    mock_transport,
)
```

## License

Apache-2.0
