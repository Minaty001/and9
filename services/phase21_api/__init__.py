"""
Phase 21 — API Manager.

Centralized external API integrations behind adapters with retries,
timeout, rate limiting, auth, caching, and fallback.

Components:
    - ApiConfig: Configuration for API manager
    - ApiRequest: API request data model
    - ApiResponse: API response data model
    - ApiAdapter: Base adapter interface with rate limiting and retries
    - ApiCache: LRU cache with TTL for API responses
    - ApiManagerService: ServiceBase wrapper
"""

from .config import ApiConfig
from .models import ApiRequest, ApiResponse
from .adapter import ApiAdapter
from .cache import ApiCache
from .service import ApiManagerService

__all__ = [
    "ApiConfig",
    "ApiRequest",
    "ApiResponse",
    "ApiAdapter",
    "ApiCache",
    "ApiManagerService",
]
