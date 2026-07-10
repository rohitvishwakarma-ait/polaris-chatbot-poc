"""
SQL Validator for GlassBot.

Inspects generated SQL strings to ensure only safe, read-only statement
types (SELECT, WITH, EXPLAIN) are allowed to be executed against Trino.
Destructive statements (DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE,
CREATE) are rejected before they reach the TrinoClient.
"""

from __future__ import annotations

import sqlparse
import sqlparse.tokens as T
from sqlparse.tokens import Keyword, DML

from chatbot.models import ValidationResult

# Statement types that are safe to execute (read-only).
ALLOWLIST: set[str] = {"SELECT", "WITH", "EXPLAIN"}

# Statement types that are destructive and must never be executed.
BLOCKLIST: set[str] = {"DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE", "CREATE"}


class SQLValidator:
    """
    Validates SQL strings against a safety allowlist/blocklist.

    Uses ``sqlparse`` to tokenise the SQL and identifies the first meaningful
    DML or Keyword token.  The validator does not require a live database
    connection.
    """

    def validate(self, sql: str) -> ValidationResult:
        """
        Validate a SQL string and return a :class:`ValidationResult`.

        Algorithm:
        1. Strip leading whitespace and comments.
        2. Parse the SQL with ``sqlparse.parse()`` to obtain a token AST.
        3. Walk the token list to find the first ``DML`` or ``Keyword``
           token, skipping whitespace and comment tokens.
        4. Normalise the token value to uppercase.
        5. Compare against ALLOWLIST / BLOCKLIST and return accordingly.
        6. If the statement type cannot be determined, reject with an
           ``"unparseable-SQL"`` error message.

        Parameters
        ----------
        sql:
            The SQL string to validate.  May contain leading whitespace,
            inline comments, or mixed case.

        Returns
        -------
        ValidationResult
            ``is_valid=True`` when the statement type is in the allowlist;
            ``is_valid=False`` with an error message otherwise.
        """
        stripped = sql.strip()

        # Parse the SQL into a list of Statement objects.
        statements = sqlparse.parse(stripped)

        if not statements:
            return ValidationResult(
                is_valid=False,
                statement_type=None,
                error_message="unparseable-SQL",
            )

        # Only inspect the first statement.
        statement = statements[0]

        # Walk the token tree to find the first DML or Keyword token,
        # skipping whitespace and comment tokens.
        keyword = self._find_first_keyword(statement)

        if keyword is None:
            return ValidationResult(
                is_valid=False,
                statement_type=None,
                error_message="unparseable-SQL",
            )

        keyword_upper = keyword.upper()

        if keyword_upper in ALLOWLIST:
            return ValidationResult(
                is_valid=True,
                statement_type=keyword_upper,
                error_message=None,
            )

        if keyword_upper in BLOCKLIST:
            return ValidationResult(
                is_valid=False,
                statement_type=keyword_upper,
                error_message=(
                    f"Destructive statement type '{keyword_upper}' is not allowed."
                ),
            )

        # Unknown statement type – treat as unparseable.
        return ValidationResult(
            is_valid=False,
            statement_type=None,
            error_message="unparseable-SQL",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_first_keyword(self, statement: sqlparse.sql.Statement) -> str | None:
        """
        Return the value of the first DML or Keyword token in *statement*,
        skipping whitespace and comment tokens.  Returns ``None`` if no
        such token is found.
        """
        for token in statement.flatten():
            # Skip whitespace and newlines.
            if token.is_whitespace:
                continue
            # Skip comment tokens.
            if token.ttype in (
                T.Comment.Single,
                T.Comment.Multiline,
            ):
                continue
            # sqlparse uses several sub-types for SQL statement keywords:
            #   Token.Keyword.DML   – SELECT, INSERT, UPDATE, DELETE
            #   Token.Keyword.DDL   – CREATE, DROP, ALTER, TRUNCATE
            #   Token.Keyword.CTE   – WITH
            #   Token.Keyword       – EXPLAIN and other generic keywords
            # We accept any of these token types as the statement keyword.
            if token.ttype in (DML, Keyword, T.Keyword.DDL, T.Keyword.CTE):
                return token.value
            # Stop at the first non-whitespace, non-comment token even if
            # it is not a DML/Keyword (e.g. a punctuation character from
            # truly malformed SQL).
            break

        return None
