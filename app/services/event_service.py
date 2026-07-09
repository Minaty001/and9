"""app/services/event_service.py"""
from app.core.service_manager import BaseService
from app.core.events import EventSystem
from app.core.memory import get_memory


class EventService(BaseService):
    name = "EventService"
    lazy = True
    ram_estimate_mb = 5

    def initialize(self):
        mem = get_memory()
        self._events = EventSystem(mem)

    def health_check(self) -> bool:
        return self._events is not None