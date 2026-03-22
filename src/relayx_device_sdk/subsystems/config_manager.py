from relayx_device_sdk.utils.subject_builder import SubjectBuilder


class ConfigManager:
    def __init__(self, transport):
        self._transport = transport

    async def get(self):
        subject = SubjectBuilder.config_get(self._transport.get_org_id())
        response = await self._transport.request(
            subject, {"id": self._transport.get_device_id()}
        )

        if response.get("status") == "DEVICE_CONFIG_FETCH_SUCCESS":
            return response.get("data", {}).get("config")
        return None

    async def set(self, data: dict) -> bool:
        subject = SubjectBuilder.config_set(self._transport.get_org_id())
        response = await self._transport.request(
            subject,
            {"id": self._transport.get_device_id(), "config": data},
        )

        return response.get("status") == "DEVICE_CONFIG_UPDATE_SUCCESS"
