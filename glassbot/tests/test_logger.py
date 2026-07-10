"""
Tests for glassbot/utils/logger.py — logging module.

Covers:
- get_logger() returns a named Logger
- Logger has StreamHandler and FileHandler configured
- Log format matches the required pattern
- Log level is read from config (defaulting to INFO when config is None)
- Named child loggers propagate correctly

Requirements: 10.3, 10.4, 10.5
"""

from __future__ import annotations

import logging
import os
import tempfile

# Suppress config singleton so tests can import the logger module freely.
os.environ.setdefault("GLASSBOT_SKIP_CONFIG", "1")


class TestGetLoggerReturnsNamedLogger:
    """get_logger(__name__) returns a Logger with the correct name."""

    def test_returns_logger_instance(self):
        # Reset configured state so each test gets a clean slate is tricky
        # because logger module is a singleton; instead we just verify the API.
        import glassbot.utils.logger as logger_module
        result = logger_module.get_logger("glassbot.test.component")
        assert isinstance(result, logging.Logger)

    def test_logger_name_matches_component(self):
        import glassbot.utils.logger as logger_module
        name = "glassbot.chatbot.metadata_service"
        result = logger_module.get_logger(name)
        assert result.name == name

    def test_different_components_return_different_loggers(self):
        import glassbot.utils.logger as logger_module
        logger_a = logger_module.get_logger("glassbot.component_a")
        logger_b = logger_module.get_logger("glassbot.component_b")
        assert logger_a is not logger_b
        assert logger_a.name != logger_b.name

    def test_same_component_returns_same_logger(self):
        """logging.getLogger() with the same name returns the identical instance."""
        import glassbot.utils.logger as logger_module
        name = "glassbot.same_component"
        first = logger_module.get_logger(name)
        second = logger_module.get_logger(name)
        assert first is second


class TestRootLoggerHandlers:
    """Root logger is configured with StreamHandler and FileHandler."""

    def _get_glassbot_handlers(self, tmp_path):
        """Run _setup_root_logger in isolation and return the handlers it added."""
        import glassbot.utils.logger as logger_module

        # Reset the singleton flag so setup runs fresh
        logger_module._configured = False

        root = logging.getLogger()
        # Snapshot existing handlers added by pytest so we can ignore them
        before = set(id(h) for h in root.handlers)

        # Point the file handler to a temp file
        import glassbot.config as config_module
        original_config = config_module.config

        class FakeConfig:
            LOG_LEVEL = "INFO"
            LOG_FILE = str(tmp_path / "test_handlers.log")

        config_module.config = FakeConfig()
        try:
            logger_module._setup_root_logger()
        finally:
            config_module.config = original_config

        added = [h for h in root.handlers if id(h) not in before]

        # Reset for subsequent tests
        for h in added:
            root.removeHandler(h)
        logger_module._configured = False
        logger_module._setup_root_logger()

        return added

    def test_root_logger_has_stream_handler(self, tmp_path):
        handlers = self._get_glassbot_handlers(tmp_path)
        # FileHandler is a subclass of StreamHandler; check for the non-file one
        stream_only = [h for h in handlers if type(h) is logging.StreamHandler]
        assert stream_only, f"Expected a StreamHandler among {handlers}"

    def test_root_logger_has_file_handler(self, tmp_path):
        handlers = self._get_glassbot_handlers(tmp_path)
        file_handlers = [h for h in handlers if isinstance(h, logging.FileHandler)]
        assert file_handlers, f"Expected a FileHandler among {handlers}"

    def test_handlers_use_correct_format(self, tmp_path):
        handlers = self._get_glassbot_handlers(tmp_path)
        expected_fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        for handler in handlers:
            fmt = handler.formatter._fmt if handler.formatter else None
            assert fmt == expected_fmt, (
                f"Handler {handler} has format {fmt!r}, expected {expected_fmt!r}"
            )


class TestLogLevelDefaults:
    """Log level defaults to INFO when config is None."""

    def test_root_logger_level_is_info_by_default(self):
        """With GLASSBOT_SKIP_CONFIG=1, config is None → level defaults to INFO."""
        import glassbot.utils.logger as logger_module  # noqa: F401 — triggers setup
        root = logging.getLogger()
        assert root.level == logging.INFO


class TestGetLoggerWithConfigOverride:
    """Verify get_logger uses config values when a Config object is available."""

    def test_logger_uses_config_log_level(self, tmp_path, monkeypatch):
        """When config.LOG_LEVEL is DEBUG, root logger should be set to DEBUG."""
        import glassbot.utils.logger as logger_module

        # Reset the module's _configured flag to simulate a fresh import
        logger_module._configured = False
        # Remove existing handlers from root so the test can assert cleanly
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_level = root.level
        root.handlers.clear()

        # Build a mock config object
        class FakeConfig:
            LOG_LEVEL = "DEBUG"
            LOG_FILE = str(tmp_path / "test_override.log")

        # Patch the config module's singleton
        import glassbot.config as config_module
        original_config = config_module.config
        config_module.config = FakeConfig()

        try:
            logger_module._setup_root_logger()
            assert root.level == logging.DEBUG
        finally:
            # Restore everything
            config_module.config = original_config
            root.handlers.clear()
            for h in original_handlers:
                root.addHandler(h)
            root.setLevel(original_level)
            logger_module._configured = False
            # Re-run setup to restore the default state
            logger_module._setup_root_logger()


class TestGetLoggerFallbackWhenConfigIsNone:
    """When config singleton is None, logger falls back to INFO + default log file."""

    def test_fallback_log_level_is_info(self):
        """Even with config=None, the logger must not raise and must default to INFO."""
        import glassbot.utils.logger as logger_module
        # Just calling get_logger must not raise regardless of config state.
        logger = logger_module.get_logger("glassbot.fallback.test")
        assert isinstance(logger, logging.Logger)
        # Root logger level should be INFO (the default)
        assert logging.getLogger().level == logging.INFO


class TestChildLoggerPropagation:
    """Named child loggers propagate messages to the root logger's handlers."""

    def test_child_logger_propagates_to_root(self, caplog):
        import glassbot.utils.logger as logger_module
        logger = logger_module.get_logger("glassbot.propagation_test")
        with caplog.at_level(logging.INFO, logger="glassbot.propagation_test"):
            logger.info("propagation check")
        assert "propagation check" in caplog.text

    def test_dunder_name_pattern_works(self):
        """Modules calling get_logger(__name__) receive a correctly named logger."""
        import glassbot.utils.logger as logger_module
        # Simulate what a module would do: get_logger(__name__)
        # __name__ for glassbot.chatbot.agent would be that string
        component = "glassbot.chatbot.agent"
        logger = logger_module.get_logger(component)
        assert logger.name == component
