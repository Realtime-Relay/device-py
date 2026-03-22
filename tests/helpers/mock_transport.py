import json
from relayx_device_sdk.transport import TransportStatus


class MockSubscription:
    def __init__(self, subject, callback, subscriptions_dict):
        self.subject = subject
        self.callback = callback
        self._unsubscribed = False
        self._subscriptions_dict = subscriptions_dict

    async def unsubscribe(self):
        self._unsubscribed = True
        if self.subject in self._subscriptions_dict:
            del self._subscriptions_dict[self.subject]


def create_mock_transport(overrides=None):
    overrides = overrides or {}

    status_callbacks = []
    subscriptions = {}
    published = []
    requests = []
    connected = [False]

    org_id = overrides.get("org_id", "test-org")
    device_id = overrides.get("device_id", "test-device")
    env = overrides.get("env", "test")
    schema = overrides.get("schema", None)
    request_handler = overrides.get("request_handler", None)

    class MockTransport:
        async def connect(self):
            if connected[0]:
                return False
            connected[0] = True
            self._emit_status({"type": TransportStatus.CONNECTED})
            return True

        async def disconnect(self):
            if not connected[0]:
                return False
            connected[0] = False
            self._emit_status({"type": TransportStatus.DISCONNECTED})
            return True

        def is_connected(self):
            return connected[0]

        async def core_subscribe(self, subject, callback):
            sub = MockSubscription(subject, callback, subscriptions)
            subscriptions[subject] = sub
            return sub

        async def subscribe(self, subject, callback):
            sub = MockSubscription(subject, callback, subscriptions)
            subscriptions[subject] = sub
            return {"subject": subject, "subscription": sub}

        async def unsubscribe(self, subscription):
            if subscription:
                subject = subscription.get("subject")
                if subject and subject in subscriptions:
                    del subscriptions[subject]

        async def publish(self, subject, data):
            published.append({"subject": subject, "data": data})
            return connected[0]

        async def request(self, subject, data, opts=None):
            requests.append({"subject": subject, "data": data, "opts": opts})
            if request_handler:
                return request_handler(subject, data, opts)
            return {"status": "OK", "data": {}}

        def on_status(self, callback):
            status_callbacks.append(callback)

        def get_org_id(self):
            return org_id

        def get_device_id(self):
            return device_id

        def get_env(self):
            return env

        def get_schema(self):
            return schema

        # Test helpers
        def _emit_status(self, event):
            for cb in status_callbacks:
                cb(event)

        def _get_subscriptions(self):
            return subscriptions

        def _get_published(self):
            return published

        def _get_requests(self):
            return requests

        def _get_status_callbacks(self):
            return status_callbacks

        def _simulate_message(self, subject, data, msg=None):
            sub = subscriptions.get(subject)
            if sub:
                sub.callback(data, msg)

        def _simulate_js_message(self, subject, data):
            sub = subscriptions.get(subject)
            if sub:
                sub.callback(data)

        def _set_connected(self, value):
            connected[0] = value

    return MockTransport()
