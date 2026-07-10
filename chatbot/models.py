"""
GlassBot domain data models.

Defines the core dataclasses used throughout the chatbot pipeline:
- ColumnInfo: metadata about a single database column
- TableMetadata: metadata about a database table (from OpenMetadata)
- QueryResult: the result of executing a SQL query via TrinoClient
- ValidationResult: the outcome of SQL validation by SQLValidator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ColumnInfo:
    """Metadata for a single database column."""

    name: str
    data_type: str
    description: str | None


@dataclass
class TableMetadata:
    """
    Metadata for a database table retrieved from OpenMetadata.

    The ``fqn`` field holds the fully qualified name in the form
    ``catalog.schema.table`` as required by Trino.
    """

    fqn: str                        # "catalog.schema.table"
    name: str
    description: str | None
    columns: list[ColumnInfo] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)  # FQNs of related tables


@dataclass
class QueryResult:
    """
    The result of executing a SQL query against Trino.

    If the query returned more than ``truncation_limit`` rows, ``truncated``
    is set to ``True`` and ``rows`` contains only the first
    ``truncation_limit`` rows.
    """

    rows: list[dict[str, Any]]
    row_count: int
    execution_time_ms: float
    truncated: bool
    truncation_limit: int | None    # None when not truncated


@dataclass
class ValidationResult:
    """
    The outcome of SQL validation by SQLValidator.

    ``statement_type`` is the uppercase keyword of the SQL statement
    (e.g. ``"SELECT"``, ``"DELETE"``), or ``None`` when the statement
    type could not be determined.
    """

    is_valid: bool
    statement_type: str | None
    error_message: str | None
