"""app/services/memory_service.py"""
from app.core.service_manager import BaseService
from app.core.memory import get_memory


class MemoryService(BaseService):
    name = "MemoryService"
    lazy = False
    ram_estimate_mb = 20

    def initialize(self):
        self._mem = get_memory()

    def health_check(self) -> bool:
        return self._mem is not None

    def shutdown(self):
        pass  # Memory persists across requests