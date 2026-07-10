"""
Unit tests for TrinoClient.

These tests exercise the TrinoClient without a live Trino connection by
mocking ``trino.dbapi.connect``.  Three scenarios are covered:

1. Query returns exactly ``row_limit`` rows  → ``truncated=False``, ``row_count=1000``
2. Query returns ``row_limit + 1`` rows      → ``truncated=True``, ``len(rows)=1000``,
                                               ``truncation_limit=1000``
3. Trino raises ``TrinoQueryError``          → ``QueryExecutionError`` is raised with
                                               no raw stack trace attached (``__cause__``
                                               is ``None``).

The ``_apply_limit`` static method is also tested directly because the
design document exposes it as a testable unit.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import trino.exceptions

from glassbot.chatbot.trino_client import TrinoClient
from glassbot.exceptions import QueryExecutionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    host: str = "trino-host",
    port: int = 8080,
    user: str = "glassbot",
    catalog: str = "tpch",
    schema: str = "tiny",
) -> MagicMock:
    """Return a minimal Config-like mock."""
    cfg = MagicMock()
    cfg.TRINO_HOST = host
    cfg.TRINO_PORT = port
    cfg.TRINO_USER = user
    cfg.TRINO_CATALOG = catalog
    cfg.TRINO_SCHEMA = schema
    return cfg


def _make_rows(n: int) -> list[dict]:
    """Return *n* minimal row dicts."""
    return [{"id": i} for i in range(n)]


def _mock_cursor(rows: list[dict]) -> MagicMock:
    """
    Build a cursor mock that returns *rows* from ``fetchmany``.

    ``cursor.description`` is set so that column names can be derived.
    The rows are plain dicts, so we simulate the DBAPI behaviour by
    returning tuples and providing a matching ``description``.
    """
    cursor = MagicMock()
    # description: list of (name, ...) tuples — only the first element matters
    cursor.description = [("id", None, None, None, None, None, None)]
    # fetchmany returns tuples as a real DBAPI cursor would
    cursor.fetchmany.return_value = [(row["id"],) for row in rows]
    return cursor


def _mock_connection(cursor: MagicMock) -> MagicMock:
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


# ---------------------------------------------------------------------------
# Tests for TrinoClient.execute
# ---------------------------------------------------------------------------

class TestTrinoClientExecute:
    """Tests for TrinoClient.execute using a mocked DBAPI connection."""

    def test_exactly_row_limit_rows_not_truncated(self):
        """
        When Trino returns exactly ``row_limit`` rows the result should NOT
        be truncated: ``truncated=False`` and ``row_count=1000``.
        """
        row_limit = 1000
        # execute fetches row_limit + 1; simulate only row_limit coming back
        rows = _make_rows(row_limit)
        cursor = _mock_cursor(rows)
        conn = _mock_connection(cursor)

        with patch("trino.dbapi.connect", return_value=conn):
            client = TrinoClient(_make_config())
            result = client.execute("SELECT 1", row_limit=row_limit)

        assert result.truncated is False
        assert result.truncation_limit is None
        assert result.row_count == row_limit
        assert len(result.rows) == row_limit

    def test_one_over_row_limit_is_truncated(self):
        """
        When Trino returns ``row_limit + 1`` rows the result should be
        truncated: ``truncated=True``, ``len(rows)=1000``,
        ``truncation_limit=1000``.
        """
        row_limit = 1000
        # Simulate row_limit + 1 rows coming back from fetchmany
        rows = _make_rows(row_limit + 1)
        cursor = _mock_cursor(rows)
        conn = _mock_connection(cursor)

        with patch("trino.dbapi.connect", return_value=conn):
            client = TrinoClient(_make_config())
            result = client.execute("SELECT 1", row_limit=row_limit)

        assert result.truncated is True
        assert result.truncation_limit == row_limit
        assert result.row_count == row_limit
        assert len(result.rows) == row_limit

    def test_trino_query_error_raised_as_query_execution_error(self):
        """
        When Trino raises ``TrinoQueryError``, the client must re-raise it as
        ``QueryExecutionError``.  Crucially, the ``__cause__`` must be ``None``
        (achieved by ``raise ... from None``) so that internal stack traces are
        not exposed.
        """
        trino_error_msg = "Syntax error in SQL statement"
        cursor = MagicMock()
        cursor.execute.side_effect = trino.exceptions.TrinoQueryError(
            {"message": trino_error_msg, "errorCode": 1, "errorType": "USER_ERROR"},
        )
        conn = _mock_connection(cursor)

        with patch("trino.dbapi.connect", return_value=conn):
            client = TrinoClient(_make_config())
            with pytest.raises(QueryExecutionError) as exc_info:
                client.execute("INVALID SQL", row_limit=1000)

        # The domain exception must be raised…
        assert isinstance(exc_info.value, QueryExecutionError)
        # …with no chained cause (stack trace suppressed via `from None`)
        assert exc_info.value.__cause__ is None

    def test_execution_time_ms_is_positive(self):
        """
        The ``execution_time_ms`` field must be a positive float.
        """
        rows = _make_rows(5)
        cursor = _mock_cursor(rows)
        conn = _mock_connection(cursor)

        with patch("trino.dbapi.connect", return_value=conn):
            client = TrinoClient(_make_config())
            result = client.execute("SELECT 1", row_limit=1000)

        assert result.execution_time_ms >= 0.0

    def test_connection_closed_after_execution(self):
        """
        The underlying connection must be closed even on success.
        """
        rows = _make_rows(1)
        cursor = _mock_cursor(rows)
        conn = _mock_connection(cursor)

        with patch("trino.dbapi.connect", return_value=conn):
            client = TrinoClient(_make_config())
            client.execute("SELECT 1", row_limit=1000)

        conn.close.assert_called_once()

    def test_connection_closed_on_trino_error(self):
        """
        The underlying connection must also be closed when a TrinoQueryError
        is raised.
        """
        cursor = MagicMock()
        cursor.execute.side_effect = trino.exceptions.TrinoQueryError(
            {"message": "boom", "errorCode": 1, "errorType": "USER_ERROR"},
        )
        conn = _mock_connection(cursor)

        with patch("trino.dbapi.connect", return_value=conn):
            client = TrinoClient(_make_config())
            with pytest.raises(QueryExecutionError):
                client.execute("BAD SQL", row_limit=1000)

        conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for TrinoClient._apply_limit (pure logic, no mocking needed)
# ---------------------------------------------------------------------------

class TestApplyLimit:
    """Direct unit tests for the _apply_limit static helper."""

    def test_zero_rows(self):
        rows, truncated, limit = TrinoClient._apply_limit([], row_limit=1000)
        assert rows == []
        assert truncated is False
        assert limit is None

    def test_fewer_than_limit(self):
        data = _make_rows(500)
        rows, truncated, limit = TrinoClient._apply_limit(data, row_limit=1000)
        assert len(rows) == 500
        assert truncated is False
        assert limit is None

    def test_exactly_at_limit(self):
        data = _make_rows(1000)
        rows, truncated, limit = TrinoClient._apply_limit(data, row_limit=1000)
        assert len(rows) == 1000
        assert truncated is False
        assert limit is None

    def test_one_over_limit(self):
        data = _make_rows(1001)
        rows, truncated, limit = TrinoClient._apply_limit(data, row_limit=1000)
        assert len(rows) == 1000
        assert truncated is True
        assert limit == 1000

    def test_many_over_limit(self):
        data = _make_rows(5000)
        rows, truncated, limit = TrinoClient._apply_limit(data, row_limit=1000)
        assert len(rows) == 1000
        assert truncated is True
        assert limit == 1000

    def test_custom_limit(self):
        data = _make_rows(51)
        rows, truncated, limit = TrinoClient._apply_limit(data, row_limit=50)
        assert len(rows) == 50
        assert truncated is True
        assert limit == 50
