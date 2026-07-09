"""app/services/intent_service.py"""
from app.core.service_manager import BaseService
from app.core.understanding import UnderstandingEngine


class IntentService(BaseService):
    name = "IntentService"
    lazy = False
    ram_estimate_mb = 5

    def initialize(self):
        self._engine = UnderstandingEngine()

    def health_check(self) -> bool:
        return self._engine is not None