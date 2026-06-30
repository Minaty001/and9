"""
Phase 1 — Error Hierarchy for JARVIS Services.

All services raise exceptions from this hierarchy, ensuring
consistent error handling and reporting.

Structure:
    JarvisError (base)
    ├── ServiceError (service-level failures)
    │   ├── InitializationError
    │   ├── ShutdownError
    │   └── HealthCheckError
    ├── ProcessingError (pipeline failures)
    │   ├── TimeoutError
    │   └── PipelineError
    ├── ValidationError (input validation)
    │   ├── InvalidQueryError
    │   └── InvalidParameterError
    └── ConfigError (configuration issues)
        ├── MissingConfigError
        └── InvalidConfigError
"""

from typing import Optional, Any


class JarvisError(Exception):
    """Base exception for all JARVIS errors.

    Attributes:
        message: Human-readable error description.
        code: Machine-readable error code (e.g., "SERVICE_INIT_FAILED").
        details: Optional structured details for debugging.
    """

    def __init__(
        self,
        message: str,
        code: str = "JARVIS_ERROR",
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Serialize error to a dictionary."""
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


# ── Service Errors ──────────────────────────────────────────────


class ServiceError(JarvisError):
    """Base service-level error."""

    def __init__(self, message: str, code: str = "SERVICE_ERROR", details: Any = None):
        super().__init__(message, code, details)


class InitializationError(ServiceError):
    """Raised when a service fails to initialize."""

    def __init__(self, message: str = "Service initialization failed", details: Any = None):
        super().__init__(message, "SERVICE_INIT_FAILED", details)


class ShutdownError(ServiceError):
    """Raised when a service fails to shut down gracefully."""

    def __init__(self, message: str = "Service shutdown failed", details: Any = None):
        super().__init__(message, "SERVICE_SHUTDOWN_FAILED", details)


class HealthCheckError(ServiceError):
    """Raised when a health check fails."""

    def __init__(self, message: str = "Health check failed", details: Any = None):
        super().__init__(message, "HEALTH_CHECK_FAILED", details)


# ── Processing Errors ───────────────────────────────────────────


class ProcessingError(JarvisError):
    """Base processing pipeline error."""

    def __init__(self, message: str, code: str = "PROCESSING_ERROR", details: Any = None):
        super().__init__(message, code, details)


class TimeoutError(ProcessingError):
    """Raised when a pipeline stage times out."""

    def __init__(self, message: str = "Processing timed out", details: Any = None):
        super().__init__(message, "PROCESSING_TIMEOUT", details)


class PipelineError(ProcessingError):
    """Raised when a pipeline stage fails."""

    def __init__(self, message: str = "Pipeline stage failed", details: Any = None):
        super().__init__(message, "PIPELINE_ERROR", details)


# ── Validation Errors ───────────────────────────────────────────


class ValidationError(JarvisError):
    """Base input validation error."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR", details: Any = None):
        super().__init__(message, code, details)


class InvalidQueryError(ValidationError):
    """Raised when the input query is invalid."""

    def __init__(self, message: str = "Invalid query", details: Any = None):
        super().__init__(message, "INVALID_QUERY", details)


class InvalidParameterError(ValidationError):
    """Raised when a parameter is invalid."""

    def __init__(self, message: str = "Invalid parameter", details: Any = None):
        super().__init__(message, "INVALID_PARAMETER", details)


# ── Config Errors ───────────────────────────────────────────────


class ConfigError(JarvisError):
    """Base configuration error."""

    def __init__(self, message: str, code: str = "CONFIG_ERROR", details: Any = None):
        super().__init__(message, code, details)


class MissingConfigError(ConfigError):
    """Raised when a required configuration is missing."""

    def __init__(self, message: str = "Missing configuration", details: Any = None):
        super().__init__(message, "MISSING_CONFIG", details)


class InvalidConfigError(ConfigError):
    """Raised when a configuration value is invalid."""

    def __init__(self, message: str = "Invalid configuration", details: Any = None):
        super().__init__(message, "INVALID_CONFIG", details)
