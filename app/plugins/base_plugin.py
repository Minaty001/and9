"""app/plugins/base_plugin.py — Plugin contract"""


class BasePlugin:
    name: str = "unnamed_plugin"
    version: str = "1.0"
    intents: list = None  # Each subclass must define its own
    ram_estimate_mb: int = 5
    lazy: bool = True

    def __init__(self):
        if self.intents is None:
            self.intents = []

    def initialize(self) -> None:
        pass

    def handle(self, intent: str, entities: dict) -> dict:
        raise NotImplementedError

    def health_check(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass