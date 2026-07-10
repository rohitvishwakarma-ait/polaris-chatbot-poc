"""
GlassBot logging module.

Provides a ``get_logger(component: str) -> logging.Logger`` factory that
returns a named child logger for any module.  The root logger is configured
once at module import time with:

  - A ``StreamHandler`` writing to stdout
  - A ``FileHandler`` writing to the path from ``config.LOG_FILE``
  - Both using the format: ``%(asctime)s | %(levelname)s | %(name)s | %(message)s``

Log level is read from ``config.LOG_LEVEL``; defaults to ``INFO``.

When ``GLASSBOT_SKIP_CONFIG=1`` is set (e.g., during unit tests), the
module-level ``config`` singleton is ``None``.  In that case the logger
falls back to ``LOG_LEVEL=INFO`` and ``LOG_FILE=glassbot.log``.
"""

from __future__ import annotations

import logging
import sys

# ---------------------------------------------------------------------------
# Defaults used when config is unavailable (e.g. GLASSBOT_SKIP_CONFIG=1)
# ---------------------------------------------------------------------------
_DEFAULT_LOG_LEVEL = "INFO"
_DEFAULT_LOG_FILE = "glassbot.log"

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

# Track whether the root logger has already been configured so we only run
# setup once even if get_logger() is called from multiple modules at import time.
_configured = False


def _setup_root_logger() -> None:
    """Configure the root logger with stdout and file handlers.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _configured
    if _configured:
        return

    # Resolve log level and log file path from config, falling back to defaults
    # when the config singleton was suppressed by GLASSBOT_SKIP_CONFIG.
    log_level_str: str = _DEFAULT_LOG_LEVEL
    log_file: str = _DEFAULT_LOG_FILE

    try:
        import config as _config_module

        cfg = getattr(_config_module, "config", None)
        if cfg is not None:
            log_level_str = getattr(cfg, "LOG_LEVEL", _DEFAULT_LOG_LEVEL) or _DEFAULT_LOG_LEVEL
            log_file = getattr(cfg, "LOG_FILE", _DEFAULT_LOG_FILE) or _DEFAULT_LOG_FILE
    except ImportError:
        pass  # config module not importable at all — use defaults

    numeric_level = getattr(logging, log_level_str.upper(), logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT)

    # --- stdout handler ---
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # --- file handler ---
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Avoid adding duplicate handlers if _configured guard somehow races.
    # We add our handlers unconditionally — the _configured flag ensures this
    # function only runs once in normal operation.
    root.addHandler(stream_handler)
    root.addHandler(file_handler)

    _configured = True


def get_logger(component: str) -> logging.Logger:
    """Return a named child logger for *component*.

    Configure the root logger on the first call so that all subsequent
    ``logging.getLogger(name)`` calls throughout the application inherit the
    same handlers and format.

    Usage::

        from utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("MetadataService initialised")

    Args:
        component: Typically ``__name__`` of the calling module; used as the
            logger name so each log entry shows which component emitted it.

    Returns:
        A :class:`logging.Logger` instance named *component*.
    """
    _setup_root_logger()
    return logging.getLogger(component)
