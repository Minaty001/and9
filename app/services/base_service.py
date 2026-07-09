"""
app/services/base_service.py — BaseService re-export

BaseService is defined in app/core/service_manager.py.
This re-export ensures all services can import cleanly.

Usage:
    from app.services.base_service import BaseService
"""

from app.core.service_manager import BaseService

__all__ = ["BaseService"]