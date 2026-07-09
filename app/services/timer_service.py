"""app/services/timer_service.py"""
from app.core.service_manager import BaseService
from app.core.timer import get_timer_service


class TimerService(BaseService):
    name = "TimerService"
    lazy = True
    ram_estimate_mb = 3

    def initialize(self):
        self._timer = get_timer_service()

    def health_check(self) -> bool:
        return self._timer is not None