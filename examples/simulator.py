import asyncio
import os
import random
import signal

from relayx_device_sdk import RelayDevice

device = RelayDevice({
    "api_key": os.environ["RELAY_API_KEY"],
    "secret": os.environ["RELAY_SECRET"],
    "mode": os.environ.get("RELAY_MODE", "test"),
})

device.connection.listeners(lambda event: print(f"[connection] {event['type']}"))


async def main():
    connected = await device.connect()
    if not connected:
        print("Failed to connect")
        return

    print("Connected. Publishing telemetry every 5s...")

    await device.config.set({
        "firmware": "v1.0.0"
    })

    print(await device.config.get())

    stop_event = asyncio.Event()

    async def publish_loop():
        while not stop_event.is_set():
            temperature = round(20 + random.random() * 15, 2)
            humidity = round(30 + random.random() * 50, 2)

            # temp_ok, hum_ok = await asyncio.gather(
            #     device.telemetry.publish("temperature", temperature),
            #     device.telemetry.publish("humidity", humidity),
            # )

            # print(
            #     f"[telemetry] temp={temperature}°C "
            #     f"({'sent' if temp_ok else 'buffered'}) | "
            #     f"humidity={humidity}% "
            #     f"({'sent' if hum_ok else 'buffered'})"
            # )

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass

    async def on_reboot(req):
        print("Rebooting....")
        print("Device rebooted!")

        data = req.payload
        print(data)

        await req.respond({
            "status": "REBOOT_OK",
            "timestamp": device.time.now(),
        })

    def on_set_config(msg):
        print(msg.payload)

    await device.rpc.listen("reboot_device", on_reboot)
    await device.command.listen("setConfig", on_set_config)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await publish_loop()

    await device.disconnect()
    print("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
