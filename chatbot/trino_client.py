"""
Polaris Trino client.

Manages the connection to Trino and executes read-only SQL queries,
returning a structured ``QueryResult``.  Results are truncated to
``row_limit`` rows (default 1 000) when Trino returns more than that,
and wall-clock execution time is captured in milliseconds.

Error handling:
    Any ``trino.exceptions.TrinoQueryError`` is caught and re-raised as a
    ``QueryExecutionError`` (a domain exception) with the Trino error
    message only — the internal Python stack trace is deliberately
    suppressed via ``raise ... from None`` so that raw tracebacks are
    never surfaced to the UI.
"""

from __future__ import annotations

import time
from typing import Optional

import trino.dbapi
import trino.exceptions

from chatbot.models import QueryResult
from config import Config
from exceptions import QueryExecutionError


class TrinoClient:
    """
    Thin wrapper around the Trino DBAPI connection.

    Parameters
    ----------
    config:
        Application configuration object.  The following fields are read:
        ``TRINO_HOST``, ``TRINO_PORT``, ``TRINO_USER``, ``TRINO_CATALOG``,
        ``TRINO_SCHEMA``.
    """

    def __init__(self, config: Config) -> None:
        self._host = config.TRINO_HOST
        self._port = config.TRINO_PORT
        self._user = config.TRINO_USER
        self._catalog = config.TRINO_CATALOG
        self._schema = config.TRINO_SCHEMA

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(self, sql: str, row_limit: int = 1000) -> QueryResult:
        """
        Execute *sql* against Trino and return a :class:`QueryResult`.

        Parameters
        ----------
        sql:
            A validated, read-only SQL string.
        row_limit:
            Maximum number of rows to return.  If Trino yields more rows
            the result is truncated and ``QueryResult.truncated`` is set
            to ``True``.

        Raises
        ------
        QueryExecutionError
            When Trino returns a query execution error.  The raw Python
            stack trace is suppressed; only the Trino error message is
            propagated.
        """
        # Trino DBAPI does not accept a trailing semicolon — strip it.
        sql = sql.strip().rstrip(";").strip()

        conn = trino.dbapi.connect(
            host=self._host,
            port=self._port,
            user=self._user,
            catalog=self._catalog,
            schema=self._schema,
        )
        try:
            cursor = conn.cursor()
            start = time.perf_counter()
            try:
                cursor.execute(sql)
                # Fetch one extra row to detect truncation without loading
                # the entire result set.
                raw_rows = cursor.fetchmany(row_limit + 1)
            except trino.exceptions.TrinoQueryError as exc:
                raise QueryExecutionError(str(exc)) from None
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000

            # Convert each row to a dict using cursor column descriptions.
            column_names = [desc[0] for desc in (cursor.description or [])]
            dict_rows = [
                dict(zip(column_names, row)) for row in raw_rows
            ]

            rows, truncated, truncation_limit = self._apply_limit(dict_rows, row_limit)

            return QueryResult(
                rows=rows,
                row_count=len(rows),
                execution_time_ms=elapsed_ms,
                truncated=truncated,
                truncation_limit=truncation_limit,
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Helper — separated for unit-testability without a live connection
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_limit(
        rows: list[dict],
        row_limit: int,
    ) -> tuple[list[dict], bool, Optional[int]]:
        """
        Apply the row-limit truncation logic to an already-fetched list.

        The caller should pass ``row_limit + 1`` rows so that this helper
        can detect whether there were *more* than ``row_limit`` rows in
        Trino without issuing a second network call.

        Returns
        -------
        (truncated_rows, truncated, truncation_limit)
        """
        if len(rows) > row_limit:
            return rows[:row_limit], True, row_limit
        return rows, False, None
