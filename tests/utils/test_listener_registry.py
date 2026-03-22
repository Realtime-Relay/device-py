from relayx_device_sdk.utils.listener_registry import ListenerRegistry


class TestListenerRegistry:
    def test_register_returns_true(self):
        reg = ListenerRegistry()
        assert reg.register("foo", lambda: None) is True

    def test_register_duplicate_returns_false(self):
        reg = ListenerRegistry()
        reg.register("foo", lambda: None)
        assert reg.register("foo", lambda: None) is False

    def test_has(self):
        reg = ListenerRegistry()
        assert reg.has("foo") is False
        reg.register("foo", lambda: None)
        assert reg.has("foo") is True

    def test_get_returns_entry(self):
        cb = lambda: None
        reg = ListenerRegistry()
        reg.register("foo", cb)
        entry = reg.get("foo")
        assert entry is not None
        assert entry["callback"] is cb
        assert entry["subscription"] is None

    def test_get_returns_none_for_missing(self):
        reg = ListenerRegistry()
        assert reg.get("foo") is None

    def test_unregister_returns_true(self):
        reg = ListenerRegistry()
        reg.register("foo", lambda: None)
        assert reg.unregister("foo") is True
        assert reg.has("foo") is False

    def test_unregister_returns_false_for_missing(self):
        reg = ListenerRegistry()
        assert reg.unregister("foo") is False

    def test_set_subscription(self):
        reg = ListenerRegistry()
        reg.register("foo", lambda: None)
        reg.set_subscription("foo", "my-sub")
        entry = reg.get("foo")
        assert entry["subscription"] == "my-sub"

    def test_set_subscription_noop_for_missing(self):
        reg = ListenerRegistry()
        reg.set_subscription("foo", "my-sub")  # should not raise
