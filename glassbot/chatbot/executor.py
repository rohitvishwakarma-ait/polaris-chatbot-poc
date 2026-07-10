"""
GlassBot Executor.

A thin coordinator that validates a SQL string and — if valid — executes it
against Trino, returning the resulting :class:`~glassbot.chatbot.models.QueryResult`.

This module is the single entry-point used by the LangGraph ``execute_query``
node so that validation and execution are an atomic step with unified error
handling.

Error handling:
    If :class:`~glassbot.utils.validators.SQLValidator` rejects the SQL, a
    :class:`~glassbot.exceptions.SQLValidationError` is raised immediately and
    :class:`~glassbot.chatbot.trino_client.TrinoClient` is never called.
"""

from __future__ import annotations

from glassbot.chatbot.models import QueryResult
from glassbot.chatbot.trino_client import TrinoClient
from glassbot.exceptions import SQLValidationError
from glassbot.utils.validators import SQLValidator


class Executor:
    """
    Validate-then-execute coordinator.

    Parameters
    ----------
    validator:
        A :class:`~glassbot.utils.validators.SQLValidator` instance used to
        check the SQL statement before it reaches Trino.
    trino_client:
        A :class:`~glassbot.chatbot.trino_client.TrinoClient` instance used
        to run the validated SQL.
    """

    def __init__(self, validator: SQLValidator, trino_client: TrinoClient) -> None:
        self._validator = validator
        self._trino_client = trino_client

    def execute(self, sql: str) -> QueryResult:
        """
        Validate *sql* and, if valid, execute it against Trino.

        Steps:
        1. Call :meth:`~glassbot.utils.validators.SQLValidator.validate` on
           *sql*.
        2. If validation fails (``is_valid == False``), raise
           :class:`~glassbot.exceptions.SQLValidationError` with the
           ``error_message`` from the
           :class:`~glassbot.chatbot.models.ValidationResult`.
        3. If validation passes, delegate to
           :meth:`~glassbot.chatbot.trino_client.TrinoClient.execute` and
           return the :class:`~glassbot.chatbot.models.QueryResult`.

        Parameters
        ----------
        sql:
            The SQL string to validate and execute.

        Returns
        -------
        QueryResult
            The result of the Trino query execution.

        Raises
        ------
        SQLValidationError
            When the SQL statement fails validation.
        QueryExecutionError
            When Trino returns a query execution error (propagated from
            :class:`~glassbot.chatbot.trino_client.TrinoClient`).
        """
        result = self._validator.validate(sql)

        if not result.is_valid:
            raise SQLValidationError(result.error_message)

        return self._trino_client.execute(sql)
