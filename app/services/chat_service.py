"""app/services/chat_service.py"""
from app.core.service_manager import BaseService


class ChatService(BaseService):
    name = "ChatService"
    lazy = False
    ram_estimate_mb = 10

    def initialize(self):
        pass  # Chat is stateless

    def health_check(self) -> bool:
        return True