from relayx_device_sdk.utils.subject_builder import SubjectBuilder


class EventManager:
    def __init__(self, transport):
        self._transport = transport

    async def send(self, event_name: str, data) -> bool:
        subject = SubjectBuilder.event(
            self._transport.get_org_id(),
            self._transport.get_env(),
            self._transport.get_device_id(),
            event_name,
        )

        return await self._transport.publish(subject, data)
