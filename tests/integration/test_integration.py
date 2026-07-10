"""
Integration tests for GlassBot.

These tests require live Trino and OpenMetadata services to be reachable.
They are excluded from the default pytest run (``addopts = -m "not integration"``
in ``pytest.ini``) and must be run explicitly:

    pytest tests/integration/ -m integration
"""

import pytest


@pytest.mark.integration
def test_trino_connectivity():
    """Verify the Trino instance is reachable and the glass bottle catalog is accessible."""
    from config import Config
    from chatbot.trino_client import TrinoClient

    cfg = Config()
    client = TrinoClient(cfg)
    result = client.execute("SELECT 1", row_limit=1)
    assert result.row_count == 1


@pytest.mark.integration
def test_openmetadata_search():
    """Verify OpenMetadata returns table metadata for glass-bottle domain terms."""
    from config import Config
    from chatbot.metadata_service import MetadataService

    cfg = Config()
    service = MetadataService(cfg)
    results = service.search_tables("glass bottle", limit=5)
    assert len(results) >= 1
    assert all(hasattr(t, "fqn") and t.fqn for t in results)


@pytest.mark.integration
def test_end_to_end_smoke():
    """End-to-end smoke test: submit a question and verify a non-empty response."""
    import uuid

    from config import Config
    from chatbot.agent import build_agent, run_agent

    cfg = Config()
    agent = build_agent(config=cfg)
    state = run_agent(agent, "How many bottles were produced last month?", str(uuid.uuid4()))
    # Either a summary or an error message — both are non-empty strings
    response = state.get("summary") or state.get("error")
    assert response and len(response) > 0
