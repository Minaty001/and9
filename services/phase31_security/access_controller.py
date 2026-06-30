"""
Phase 31 — Access Controller.

Checks if a given user/token has permission to execute a specific
tool/operation. Integrates with AuthManager for token validation
and AuditLogger for logging.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .auth import AuthManager
from .audit import AuditLogger
from .models import SecurityEvent

logger = logging.getLogger(__name__)


# Default tool permission matrix: tool_name -> required_scope
DEFAULT_TOOL_SCOPES: Dict[str, str] = {
    # Core tools
    "validate": "read",
    "sanitize": "read",
    "encrypt": "write",
    "decrypt": "read",
    "audit_log": "read",
    "export_audit": "admin",
    # Secret management
    "store_secret": "admin",
    "get_secret": "read",
    "list_secrets": "read",
    "revoke_secret": "admin",
    "rotate_secret": "admin",
    # Token management
    "generate_token": "admin",
    "revoke_token": "admin",
    # System
    "health": "read",
    "stats": "read",
    "shutdown": "admin",
}


class AccessController:
    """Controls access to tools/operations based on token authentication.

    Usage:
        ctrl = AccessController(auth_manager, audit_logger)
        granted = ctrl.check_access(token, "encrypt", {"data": "..."})
    """

    def __init__(
        self,
        auth_manager: AuthManager,
        audit_logger: Optional[AuditLogger] = None,
        tool_scopes: Optional[Dict[str, str]] = None,
    ):
        """Initialize the access controller.

        Args:
            auth_manager: An AuthManager instance for token validation.
            audit_logger: Optional AuditLogger for logging access attempts.
            tool_scopes: Optional custom tool-to-scope mapping.
        """
        self._auth = auth_manager
        self._audit = audit_logger
        self._tool_scopes = {**DEFAULT_TOOL_SCOPES, **(tool_scopes or {})}

    def check_access(self, token: str, tool_name: str, args: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a token has permission to execute a specific tool.

        Args:
            token: The authentication token.
            tool_name: The name of the tool/operation.
            args: Optional arguments passed to the tool (for future context-aware checks).

        Returns:
            True if access is granted.
        """
        # Validate the token first
        if not self._auth.authenticate(token):
            self._log_access_attempt(token, tool_name, granted=False)
            return False

        # Look up required scope for the tool
        required_scope = self._tool_scopes.get(tool_name, "admin")  # default restrict to admin

        # Check if token has the required scope
        granted = self._auth.validate_scope(token, required_scope)

        self._log_access_attempt(token, tool_name, granted=granted, args=args)
        return granted

    def register_tool_scope(self, tool_name: str, required_scope: str) -> None:
        """Register or update the required scope for a tool.

        Args:
            tool_name: The tool/operation name.
            required_scope: The required scope (e.g., "read", "write", "admin").
        """
        self._tool_scopes[tool_name] = required_scope
        logger.debug("Registered scope '%s' for tool '%s'", required_scope, tool_name)

    def get_tool_scopes(self) -> Dict[str, str]:
        """Get the current tool-to-scope mapping.

        Returns:
            Dict of tool_name -> required_scope.
        """
        return dict(self._tool_scopes)

    def _log_access_attempt(
        self,
        token: str,
        tool: str,
        granted: bool,
        args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an access attempt via AuditLogger.

        Args:
            token: The token used.
            tool: The tool attempted.
            granted: Whether access was granted.
            args: Optional arguments.
        """
        if not self._audit:
            return

        user_id = self._auth.get_user_id(token) or "unknown"
        event = SecurityEvent(
            event_type="access_control",
            severity="low" if granted else "medium",
            source="AccessController",
            user_id=user_id,
            details={
                "tool": tool,
                "granted": granted,
                "args_keys": list(args.keys()) if args else [],
            },
            blocked=not granted,
        )
        self._audit.log_event(event)
