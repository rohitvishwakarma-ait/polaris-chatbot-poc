"""
GlassBot domain exception hierarchy.

All application-level exceptions derive from ``GlassBotError`` so callers can
catch the entire family with a single ``except GlassBotError`` clause, or
target a specific sub-class for granular error handling.
"""


class GlassBotError(Exception):
    """Base class for all GlassBot application errors."""


class MetadataConnectivityError(GlassBotError):
    """Raised when the OpenMetadata service is unreachable (network / timeout)."""


class MetadataNotFoundError(GlassBotError):
    """Raised when OpenMetadata returns no tables matching the user question."""


class SQLValidationError(GlassBotError):
    """Raised when the SQLValidator rejects a generated SQL statement."""


class QueryExecutionError(GlassBotError):
    """Raised when Trino returns a query execution error."""


class LLMError(GlassBotError):
    """Raised when an LLM API call fails or times out."""


class ConfigurationError(GlassBotError):
    """Raised at startup when a required environment variable is missing or invalid."""
