import asyncio
import base64
import json
import inspect
import uuid

import msgpack
import nats
from nats.aio.client import RawCredentials
import nats.js.api as js_api

from relayx_device_sdk.errors import (
    NotConnectedError,
    TimeoutError,
    ValidationError,
)
from relayx_device_sdk.utils.subject_builder import SubjectBuilder


class TransportStatus:
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    RECONNECTED = "reconnected"
    AUTH_FAILED = "auth_failed"
    RECONNECT_FAILED = "reconnect_failed"


NATS_SERVERS_PRODUCTION = [
    "tls://api.relay-x.io:4221",
    "tls://api.relay-x.io:4222",
    "tls://api.relay-x.io:4223",
]

NATS_SERVERS_TEST = [
    "nats://0.0.0.0:4221",
    "nats://0.0.0.0:4222",
    "nats://0.0.0.0:4223",
]


class NatsTransport:
    def __init__(self, config: dict):
        self._config = config
        self._env = config["mode"]

        self._nats_client = None
        self._jetstream = None
        self._js_manager = None

        self._connected = False
        self._status_callbacks: list = []
        self._consumer_map: dict = {}

        self._org_id: str | None = None
        self._device_id: str | None = None
        self._stream_name: str | None = None
        self._command_queue_stream_name: str | None = None

        self._offline_message_buffer: list = []
        self._schema: dict | None = None

        self._message_loops: list[asyncio.Task] = []

    async def connect(self) -> bool:
        if self._connected:
            return False

        creds_file = self._build_creds_file(
            self._config["api_key"], self._config["secret"]
        )
        creds = RawCredentials(creds_file)

        servers = (
            NATS_SERVERS_PRODUCTION
            if self._config["mode"] == "production"
            else NATS_SERVERS_TEST
        )

        self._nats_client = await nats.connect(
            servers=servers,
            no_echo=True,
            max_reconnect_attempts=1200,
            reconnect_time_wait=1,
            allow_reconnect=True,
            token=self._config["api_key"],
            user_credentials=creds,
            reconnected_cb=self._on_reconnect,
            disconnected_cb=self._on_disconnect,
            error_cb=self._on_error,
            closed_cb=self._on_closed,
        )

        self._jetstream = self._nats_client.jetstream()
        self._js_manager = self._nats_client.jsm()

        self._decode_api_key(self._config["api_key"])

        self._connected = True

        await self._fetch_schema()

        self._emit_status({"type": TransportStatus.CONNECTED})

        return True

    async def disconnect(self) -> bool:
        if not self._connected:
            return False

        await self._delete_all_consumers()
        self._offline_message_buffer.clear()

        for task in self._message_loops:
            task.cancel()
        self._message_loops.clear()

        if self._nats_client:
            await self._nats_client.drain()

        self._connected = False
        self._emit_status({"type": TransportStatus.DISCONNECTED})

        return True

    def is_connected(self) -> bool:
        return self._connected

    async def core_subscribe(self, subject: str, callback):
        if not self._connected:
            raise NotConnectedError()
        if not callable(callback):
            raise ValidationError("callback must be a function")

        sub = await self._nats_client.subscribe(subject)

        async def _message_loop():
            try:
                async for msg in sub.messages:
                    try:
                        data = json.loads(msg.data.decode("utf-8"))
                        if inspect.iscoroutinefunction(callback):
                            await callback(data, msg)
                        else:
                            callback(data, msg)
                    except Exception:
                        pass
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(_message_loop())
        self._message_loops.append(task)

        return sub

    async def subscribe(self, subject: str, callback):
        if not self._connected:
            raise NotConnectedError()
        if not callable(callback):
            raise ValidationError("callback must be a function")

        consumer_name = f"device_{uuid.uuid4()}_consumer"

        sub = await self._jetstream.subscribe(
            subject,
            stream=self._command_queue_stream_name,
            config=js_api.ConsumerConfig(
                name=consumer_name,
                deliver_policy=js_api.DeliverPolicy.NEW,
                ack_policy=js_api.AckPolicy.EXPLICIT,
            ),
        )

        async def _consume_loop():
            try:
                async for msg in sub.messages:
                    try:
                        data = msgpack.unpackb(msg.data, raw=False)
                        if inspect.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                        await msg.ack()
                    except Exception:
                        await msg.nak(delay=5)
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(_consume_loop())
        self._message_loops.append(task)

        subscription = {"subject": subject, "subscription": sub, "consumer": sub}
        self._consumer_map[subject] = subscription

        return subscription

    async def unsubscribe(self, subscription) -> None:
        if subscription is None:
            return

        subject = subscription.get("subject")
        sub = subscription.get("subscription")

        if sub:
            try:
                await sub.unsubscribe()
            except Exception:
                pass

        if subject and subject in self._consumer_map:
            del self._consumer_map[subject]

    async def publish(self, subject: str, data) -> bool:
        if not self._connected:
            self._offline_message_buffer.append({"subject": subject, "data": data})
            return False

        encoded = msgpack.packb(data)
        try:
            ack = await self._jetstream.publish(subject, encoded)
            return ack is not None
        except Exception:
            return False

    async def request(self, subject: str, data, opts: dict | None = None):
        if not self._connected:
            raise NotConnectedError()

        timeout_ms = (opts or {}).get("timeout", 20000)
        timeout_sec = timeout_ms / 1000

        encoded = json.dumps(data).encode("utf-8")

        try:
            response = await self._nats_client.request(
                subject, encoded, timeout=timeout_sec
            )
            return json.loads(response.data.decode("utf-8"))
        except nats.errors.TimeoutError:
            raise TimeoutError(subject)

    def get_schema(self) -> dict | None:
        return self._schema

    def on_status(self, callback) -> None:
        self._status_callbacks.append(callback)

    def get_org_id(self) -> str:
        return self._org_id

    def get_device_id(self) -> str:
        return self._device_id

    def get_env(self) -> str:
        return self._env

    def _emit_status(self, event: dict) -> None:
        for cb in self._status_callbacks:
            try:
                if inspect.iscoroutinefunction(cb):
                    asyncio.create_task(cb(event))
                else:
                    cb(event)
            except Exception:
                pass

    async def _on_disconnect(self):
        self._connected = False
        self._emit_status({"type": TransportStatus.DISCONNECTED})

    async def _on_reconnect(self):
        self._connected = True
        await self._flush_offline_buffer()
        self._emit_status({"type": TransportStatus.RECONNECTED})

    async def _on_error(self, e):
        if "Authorization Violation" in str(e):
            self._connected = False
            self._emit_status({"type": TransportStatus.AUTH_FAILED, "error": e})

    async def _on_closed(self):
        self._connected = False
        self._offline_message_buffer.clear()

    async def _flush_offline_buffer(self):
        messages = self._offline_message_buffer[:]
        self._offline_message_buffer.clear()
        for msg in messages:
            await self.publish(msg["subject"], msg["data"])

    async def _delete_all_consumers(self):
        for subject, sub_info in list(self._consumer_map.items()):
            sub = sub_info.get("subscription")
            if sub:
                try:
                    await sub.unsubscribe()
                except Exception:
                    pass
        self._consumer_map.clear()

    async def _fetch_schema(self):
        try:
            subject = SubjectBuilder.schema_get(self._org_id)
            response = await self.request(subject, {"id": self._device_id})
            self._schema = response.get("data", {}).get("schema", None)
        except Exception:
            self._schema = None

    def _decode_api_key(self, api_key: str) -> None:
        parts = api_key.split(".")
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes)

        self._org_id = payload["nats"]["org_data"]["org_id"]
        self._device_id = payload["nats"]["org_data"]["api_key_id"]
        self._stream_name = f"{self._org_id}_stream"
        self._command_queue_stream_name = f"{self._org_id}_command_queue"

    @staticmethod
    def _build_creds_file(jwt: str, secret: str) -> str:
        jwt = jwt.strip()
        secret = secret.strip()
        return (
            f"-----BEGIN NATS USER JWT-----\n"
            f"{jwt}\n"
            f"------END NATS USER JWT------\n"
            f"\n"
            f"************************* IMPORTANT *************************\n"
            f"NKEY Seed printed below can be used to sign and prove identity.\n"
            f"NKEYs are sensitive and should be treated as secrets.\n"
            f"\n"
            f"-----BEGIN USER NKEY SEED-----\n"
            f"{secret}\n"
            f"------END USER NKEY SEED------\n"
            f"\n"
            f"*************************************************************"
        )
