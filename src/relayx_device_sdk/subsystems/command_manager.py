import inspect

from relayx_device_sdk.errors import DuplicateListenerError, ValidationError
from relayx_device_sdk.utils.listener_registry import ListenerRegistry
from relayx_device_sdk.utils.subject_builder import SubjectBuilder


class CommandMessage:
    def __init__(self, payload):
        self.payload = payload


class CommandManager:
    def __init__(self, transport):
        self._transport = transport
        self._registry = ListenerRegistry()

    async def listen(self, name: str, callback):
        if not callable(callback):
            raise ValidationError("callback must be a function")

        if self._registry.has(name):
            raise DuplicateListenerError(name)

        subject = SubjectBuilder.command(
            self._transport.get_org_id(),
            self._transport.get_env(),
            self._transport.get_device_id(),
            name,
        )

        def _on_message(data):
            msg = CommandMessage(data)
            if inspect.iscoroutinefunction(callback):
                import asyncio
                asyncio.create_task(callback(msg))
            else:
                callback(msg)

        subscription = await self._transport.subscribe(subject, _on_message)

        self._registry.register(name, callback)
        self._registry.set_subscription(name, subscription)

    async def off(self, name: str) -> bool:
        entry = self._registry.get(name)
        if entry is None:
            return False

        subscription = entry.get("subscription")
        if subscription:
            await self._transport.unsubscribe(subscription)

        self._registry.unregister(name)
        return True
