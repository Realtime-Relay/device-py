import asyncio
import inspect
import json

from relayx_device_sdk.errors import DuplicateListenerError, ValidationError
from relayx_device_sdk.utils.listener_registry import ListenerRegistry
from relayx_device_sdk.utils.subject_builder import SubjectBuilder


class RpcRequest:
    def __init__(self, payload, msg):
        self.payload = payload
        self._msg = msg

    async def respond(self, data):
        response = json.dumps({"status": "ok", "data": data}).encode("utf-8")
        await self._msg.respond(response)

    async def error(self, data):
        response = json.dumps({"status": "error", "data": data}).encode("utf-8")
        await self._msg.respond(response)


class RpcManager:
    def __init__(self, transport):
        self._transport = transport
        self._registry = ListenerRegistry()

    async def listen(self, name: str, callback):
        if not callable(callback):
            raise ValidationError("callback must be a function")

        if self._registry.has(name):
            raise DuplicateListenerError(name)

        subject = SubjectBuilder.rpc(
            self._transport.get_org_id(),
            self._transport.get_env(),
            self._transport.get_device_id(),
            name,
        )

        async def _on_message(data, msg):
            request = RpcRequest(data, msg)
            if inspect.iscoroutinefunction(callback):
                await callback(request)
            else:
                callback(request)

        subscription = await self._transport.core_subscribe(subject, _on_message)

        self._registry.register(name, callback)
        self._registry.set_subscription(name, subscription)

    async def off(self, name: str) -> bool:
        entry = self._registry.get(name)
        if entry is None:
            return False

        subscription = entry.get("subscription")
        if subscription:
            try:
                await subscription.unsubscribe()
            except Exception as e:
                self._transport.logger.error('Failed to unsubscribe RPC listener', e)

        self._registry.unregister(name)
        return True
