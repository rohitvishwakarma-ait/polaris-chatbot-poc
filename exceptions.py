"""
Polaris domain exception hierarchy.

All application-level exceptions derive from ``PolarisError`` so callers can
catch the entire family with a single ``except PolarisError`` clause, or
target a specific sub-class for granular error handling.

For backward compatibility, ``GlassBotError`` is kept as an alias.
"""


class PolarisError(Exception):
    """Base class for all Polaris application errors."""


# Backward compatibility alias
GlassBotError = PolarisError


class MetadataConnectivityError(PolarisError):
    """Raised when the OpenMetadata service is unreachable (network / timeout)."""


class MetadataNotFoundError(PolarisError):
    """Raised when OpenMetadata returns no tables matching the user question."""


class SQLValidationError(PolarisError):
    """Raised when the SQLValidator rejects a generated SQL statement."""


class QueryExecutionError(PolarisError):
    """Raised when Trino returns a query execution error."""


class LLMError(PolarisError):
    """Raised when an LLM API call fails or times out."""


class ConfigurationError(PolarisError):
    """Raised at startup when a required environment variable is missing or invalid."""
