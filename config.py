"""
Polaris configuration module.

Reads all external-service settings from environment variables (or a ``.env``
file loaded by ``python-dotenv``) using simple os.environ access.  A
``ConfigurationError`` is raised at *import time* if any required variable is
absent, ensuring the application exits with a clear message before the UI loads.

Required variables (absence causes a startup error):
    LLM_PROVIDER, TRINO_HOST, OPENMETADATA_URL, OPENMETADATA_API_TOKEN

Optional (have sensible defaults for Docker Compose):
    TRINO_PORT, TRINO_CATALOG, TRINO_SCHEMA, TRINO_USER, APP_NAME
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

from exceptions import ConfigurationError

# Load .env file if present (no-op when the file does not exist)
load_dotenv()

# ---------------------------------------------------------------------------
# Names of variables that must be present for the application to start.
# ---------------------------------------------------------------------------
REQUIRED_CONFIG_VARS: tuple[str, ...] = (
    "LLM_PROVIDER",
    "TRINO_HOST",
    "OPENMETADATA_URL",
    "OPENMETADATA_API_TOKEN",
)


def _require(name: str) -> str:
    """Return the value of *name* from the environment or raise ConfigurationError."""
    value = os.environ.get(name)
    if not value:
        raise ConfigurationError(
            f"Required environment variable '{name}' is missing or empty. "
            f"Set it in your shell or in the .env file before starting Polaris."
        )
    return value


def _optional(name: str) -> Optional[str]:
    """Return the value of *name* from the environment, or None if absent/empty."""
    value = os.environ.get(name)
    return value if value else None


class Config:
    """
    Centralised configuration for Polaris.

    All fields are populated from environment variables at instantiation.
    Pass ``env`` as a mapping to override the real environment (useful for
    testing).

    Example::

        cfg = Config()          # reads from os.environ / .env
        cfg = Config(env={...}) # override for tests
    """

    def __init__(self, env: Optional[dict[str, str]] = None) -> None:
        _env = env  # None means "use os.environ"

        def get_required(name: str) -> str:
            if _env is not None:
                value = _env.get(name)
                if not value:
                    raise ConfigurationError(
                        f"Required environment variable '{name}' is missing or empty. "
                        f"Set it in your shell or in the .env file before starting Polaris."
                    )
                return value
            return _require(name)

        def get_optional(name: str) -> Optional[str]:
            if _env is not None:
                value = _env.get(name)
                return value if value else None
            return _optional(name)

        def get_int(name: str, default: int) -> int:
            raw = get_optional(name)
            if raw is None:
                return default
            try:
                return int(raw)
            except ValueError:
                raise ConfigurationError(
                    f"Environment variable '{name}' must be an integer, got: {raw!r}"
                )

        # ---- Application branding -------------------------------------------
        self.APP_NAME: str = get_optional("APP_NAME") or "Polaris"

        # ---- LLM provider --------------------------------------------------
        self.LLM_PROVIDER: str = get_required("LLM_PROVIDER")

        # OPENAI_API_KEY is conditionally required (needed for openai provider).
        self.OPENAI_API_KEY: Optional[str] = get_optional("OPENAI_API_KEY")
        self.AZURE_OPENAI_ENDPOINT: Optional[str] = get_optional("AZURE_OPENAI_ENDPOINT")
        self.AZURE_OPENAI_API_KEY: Optional[str] = get_optional("AZURE_OPENAI_API_KEY")
        self.ANTHROPIC_API_KEY: Optional[str] = get_optional("ANTHROPIC_API_KEY")
        self.OLLAMA_BASE_URL: Optional[str] = get_optional("OLLAMA_BASE_URL")

        # ---- Cloudflare Workers AI (optional — used when LLM_PROVIDER == "cloudflare") ---
        self.CLOUDFLARE_ACCOUNT_ID: Optional[str] = get_optional("CLOUDFLARE_ACCOUNT_ID")
        self.CLOUDFLARE_AIG_TOKEN: Optional[str] = get_optional("CLOUDFLARE_AIG_TOKEN")
        self.CLOUDFLARE_MODEL: Optional[str] = get_optional("CLOUDFLARE_MODEL")

        # ---- Trino ---------------------------------------------------------
        self.TRINO_HOST: str = get_required("TRINO_HOST")
        self.TRINO_PORT: int = get_int("TRINO_PORT", default=8080)
        self.TRINO_CATALOG: str = get_optional("TRINO_CATALOG") or "system"
        self.TRINO_SCHEMA: str = get_optional("TRINO_SCHEMA") or "runtime"
        self.TRINO_USER: str = get_optional("TRINO_USER") or "polaris"

        # ---- OpenMetadata --------------------------------------------------
        self.OPENMETADATA_URL: str = get_required("OPENMETADATA_URL")
        self.OPENMETADATA_API_TOKEN: str = get_required("OPENMETADATA_API_TOKEN")

        # ---- Logging -------------------------------------------------------
        self.LOG_LEVEL: str = get_optional("LOG_LEVEL") or "INFO"
        self.LOG_FILE: str = get_optional("LOG_FILE") or "polaris.log"


# ---------------------------------------------------------------------------
# Module-level singleton — created at import time during normal application
# startup.  The ``POLARIS_SKIP_CONFIG`` environment variable can be set to
# any non-empty value to suppress singleton creation; this is intended
# exclusively for unit tests that import ``Config`` without a full environment.
# ---------------------------------------------------------------------------
if not os.environ.get("POLARIS_SKIP_CONFIG") and not os.environ.get("GLASSBOT_SKIP_CONFIG"):
    try:
        config = Config()
    except ConfigurationError:
        # Re-raise so the process exits at startup with a useful message.
        raise
else:
    config = None  # type: ignore[assignment]
