from typing import Any, Callable


class ListenerRegistry:
    def __init__(self):
        self._listeners: dict[str, dict] = {}

    def register(self, name: str, callback: Callable) -> bool:
        if name in self._listeners:
            return False
        self._listeners[name] = {"callback": callback, "subscription": None}
        return True

    def unregister(self, name: str) -> bool:
        if name not in self._listeners:
            return False
        del self._listeners[name]
        return True

    def has(self, name: str) -> bool:
        return name in self._listeners

    def get(self, name: str) -> dict | None:
        return self._listeners.get(name)

    def set_subscription(self, name: str, subscription: Any) -> None:
        if name in self._listeners:
            self._listeners[name]["subscription"] = subscription
