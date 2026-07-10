"""
Tests for glassbot/config.py — configuration loading and validation.

Includes the Property 11 property-based test:
    Missing Configuration Variable Error

**Validates: Requirements 11.3**
"""

import os

# Suppress the module-level Config() singleton so this file can be imported
# without a fully-populated environment (tests supply their own env dicts).
os.environ.setdefault("GLASSBOT_SKIP_CONFIG", "1")

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from config import Config, REQUIRED_CONFIG_VARS
from exceptions import ConfigurationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _full_env() -> dict[str, str]:
    """Return a minimal environment dict with all required variables present."""
    return {
        "LLM_PROVIDER": "openai:gpt-4o",
        "TRINO_HOST": "localhost",
        "TRINO_CATALOG": "glass_bottle",
        "TRINO_SCHEMA": "manufacturing",
        "OPENMETADATA_URL": "http://localhost:8585",
        "OPENMETADATA_API_TOKEN": "test-token",
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestConfigDefaults:
    """Verify default values and optional fields when all required vars are present."""

    def test_required_fields_loaded(self):
        env = _full_env()
        cfg = Config(env=env)
        assert cfg.LLM_PROVIDER == "openai:gpt-4o"
        assert cfg.TRINO_HOST == "localhost"
        assert cfg.TRINO_CATALOG == "glass_bottle"
        assert cfg.TRINO_SCHEMA == "manufacturing"
        assert cfg.OPENMETADATA_URL == "http://localhost:8585"
        assert cfg.OPENMETADATA_API_TOKEN == "test-token"

    def test_trino_port_default(self):
        cfg = Config(env=_full_env())
        assert cfg.TRINO_PORT == 8080

    def test_trino_port_override(self):
        env = {**_full_env(), "TRINO_PORT": "9090"}
        cfg = Config(env=env)
        assert cfg.TRINO_PORT == 9090

    def test_trino_user_default(self):
        cfg = Config(env=_full_env())
        assert cfg.TRINO_USER == "glassbot"

    def test_trino_user_override(self):
        env = {**_full_env(), "TRINO_USER": "analyst"}
        cfg = Config(env=env)
        assert cfg.TRINO_USER == "analyst"

    def test_log_level_default(self):
        cfg = Config(env=_full_env())
        assert cfg.LOG_LEVEL == "INFO"

    def test_log_file_default(self):
        cfg = Config(env=_full_env())
        assert cfg.LOG_FILE == "glassbot.log"

    def test_optional_fields_are_none_when_absent(self):
        cfg = Config(env=_full_env())
        assert cfg.OPENAI_API_KEY is None
        assert cfg.AZURE_OPENAI_ENDPOINT is None
        assert cfg.AZURE_OPENAI_API_KEY is None
        assert cfg.ANTHROPIC_API_KEY is None
        assert cfg.OLLAMA_BASE_URL is None

    def test_optional_fields_populated_when_present(self):
        env = {
            **_full_env(),
            "OPENAI_API_KEY": "sk-abc123",
            "AZURE_OPENAI_ENDPOINT": "https://myresource.openai.azure.com/",
            "ANTHROPIC_API_KEY": "ant-key",
            "OLLAMA_BASE_URL": "http://localhost:11434",
        }
        cfg = Config(env=env)
        assert cfg.OPENAI_API_KEY == "sk-abc123"
        assert cfg.AZURE_OPENAI_ENDPOINT == "https://myresource.openai.azure.com/"
        assert cfg.ANTHROPIC_API_KEY == "ant-key"
        assert cfg.OLLAMA_BASE_URL == "http://localhost:11434"

    def test_trino_port_non_integer_raises_config_error(self):
        env = {**_full_env(), "TRINO_PORT": "not-a-number"}
        with pytest.raises(ConfigurationError):
            Config(env=env)


class TestMissingRequiredVariables:
    """Ensure each required variable independently triggers ConfigurationError."""

    @pytest.mark.parametrize("missing_var", REQUIRED_CONFIG_VARS)
    def test_each_required_variable_raises(self, missing_var: str):
        env = {v: "placeholder" for v in REQUIRED_CONFIG_VARS if v != missing_var}
        with pytest.raises(ConfigurationError) as exc_info:
            Config(env=env)
        assert missing_var in str(exc_info.value), (
            f"Expected error message to contain the variable name '{missing_var}', "
            f"got: {exc_info.value}"
        )

    def test_empty_string_treated_as_missing(self):
        env = {**_full_env(), "TRINO_HOST": ""}
        with pytest.raises(ConfigurationError) as exc_info:
            Config(env=env)
        assert "TRINO_HOST" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Property-based test — Property 11: Missing Configuration Variable Error
#
# For any required configuration variable that is absent from the environment
# at startup, Config initialisation SHALL raise a ConfigurationError whose
# message contains the name of the missing variable.
#
# **Validates: Requirements 11.3**
# ---------------------------------------------------------------------------

@given(st.sampled_from(REQUIRED_CONFIG_VARS))
@settings(max_examples=100)
def test_missing_config_raises_with_var_name(missing_var: str):
    """
    Property 11: Missing Configuration Variable Error
    **Validates: Requirements 11.3**

    For any required configuration variable that is absent from the environment,
    Config() SHALL raise ConfigurationError with the variable name in the message.
    """
    # Build an env dict that has every required variable EXCEPT the one under test
    env = {v: "placeholder" for v in REQUIRED_CONFIG_VARS if v != missing_var}

    with pytest.raises(ConfigurationError) as exc_info:
        Config(env=env)

    assert missing_var in str(exc_info.value), (
        f"ConfigurationError message did not contain the missing variable name "
        f"'{missing_var}'. Got: {exc_info.value!r}"
    )
