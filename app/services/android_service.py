"""app/services/android_service.py"""
from app.core.service_manager import BaseService


class AndroidService(BaseService):
    name = "AndroidService"
    lazy = True
    ram_estimate_mb = 15

    def initialize(self):
        pass  # Android actions are stateless handlers

    def health_check(self) -> bool:
        try:
            from app.android.action_registry import validate_registry
            validate_registry()
            return True
        except Exception:
            return False