"""
MetadataService — OpenMetadata integration for Polaris.

Queries the OpenMetadata REST API to retrieve table metadata relevant to a
user question.

Key behaviour:
- Extracts short keyword tokens from the user question before searching,
  so that natural language phrases like "Give me completed production orders"
  become a focused query like "production orders" that OpenMetadata can match.
- When OpenMetadata returns no results for the extracted keywords, falls back
  to a broad search using each token individually.
- If all searches return empty, falls back to Trino information_schema
  introspection to discover available tables dynamically.

Error taxonomy:
    ``MetadataNotFoundError``  — raised when no tables can be found at all.
    ``MetadataConnectivityError`` — raised on network / HTTP connectivity failure.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import httpx

from chatbot.models import ColumnInfo, TableMetadata
from exceptions import MetadataConnectivityError, MetadataNotFoundError

logger = logging.getLogger(__name__)

_SEARCH_PATH = "/api/v1/search/query"
_DEFAULT_INDEX = "table_search_index"

# Stop-words to strip before sending to OpenMetadata
_STOP_WORDS = {
    "give", "me", "show", "get", "list", "find", "fetch", "tell", "what",
    "how", "many", "much", "the", "a", "an", "of", "in", "on", "at", "to",
    "for", "is", "are", "was", "were", "all", "by", "with", "from", "where",
    "that", "which", "have", "has", "been", "be", "do", "does", "did",
    "number", "count", "total",
}


def _extract_keywords(question: str) -> str:
    """Extract meaningful keywords from a natural language question.

    Strips punctuation, lowercases, removes stop-words, and returns a
    space-separated string of the remaining tokens.  Falls back to the
    original question if nothing meaningful remains.

    Examples:
        "Give me completed production orders" → "completed production orders"
        "How many machines are running?"      → "machines running"
    """
    cleaned = re.sub(r"[^\w\s]", " ", question.lower())
    tokens = [t for t in cleaned.split() if t and t not in _STOP_WORDS and len(t) > 2]
    if not tokens:
        return question
    return " ".join(tokens)


class MetadataService:
    """Fetches table metadata from OpenMetadata via its REST search API.

    When OpenMetadata returns no results, falls back to Trino
    information_schema introspection if a Trino client is provided.
    """

    def __init__(self, config: Any, trino_client: Optional[Any] = None) -> None:
        """
        Args:
            config: Application config with OPENMETADATA_URL and OPENMETADATA_API_TOKEN.
            trino_client: Optional TrinoClient for fallback introspection.
        """
        self._base_url: str = config.OPENMETADATA_URL.rstrip("/")
        self._token: str = config.OPENMETADATA_API_TOKEN
        self._trino_client = trino_client

    def search_tables(self, question: str, limit: int = 10) -> list[TableMetadata]:
        """Search OpenMetadata for tables relevant to *question*.

        Search strategy (in order):
        1. Search with extracted keywords from the question.
        2. If empty, search for each individual keyword token.
        3. If still empty, fall back to Trino information_schema introspection.
        4. If that also fails, raise MetadataNotFoundError.

        Args:
            question: The user's natural language question.
            limit:    Maximum number of tables to return (default: 10).

        Returns:
            A list of ``TableMetadata`` objects.

        Raises:
            MetadataNotFoundError:     When no tables can be found anywhere.
            MetadataConnectivityError: On network / HTTP connectivity failure.
        """
        keywords = _extract_keywords(question)
        logger.debug(
            "Metadata search: question=%r → keywords=%r", question, keywords
        )

        # Attempt 1: search with extracted keywords
        hits = self._search(keywords, limit)

        # Attempt 2: try each individual token if first attempt failed
        if not hits:
            tokens = keywords.split()
            for token in tokens:
                hits = self._search(token, limit)
                if hits:
                    logger.info(
                        "Metadata found using fallback token %r for question: %r",
                        token, question,
                    )
                    break

        # Attempt 3: broad search with wildcard
        if not hits:
            hits = self._search("*", limit)

        if hits:
            tables = [_parse_table(hit["_source"]) for hit in hits]
            logger.debug("Found %d table(s) for question %r", len(tables), question)
            return tables

        # Attempt 4: Trino information_schema introspection
        if self._trino_client:
            logger.info(
                "No OpenMetadata results for %r — falling back to Trino introspection",
                question,
            )
            introspected = self._introspect_trino(limit)
            if introspected:
                return introspected

        # Nothing found anywhere
        logger.warning("No table metadata found for question: %r", question)
        raise MetadataNotFoundError(
            "No tables found. Please configure data sources in the Data Sources page."
        )

    def get_all_tables(self, limit: int = 50) -> list[TableMetadata]:
        """Retrieve all available tables from OpenMetadata (or Trino fallback).

        Used by the dynamic prompt builder to get the full schema context.

        Args:
            limit: Maximum number of tables to return.

        Returns:
            A list of all discoverable TableMetadata objects.
        """
        # Try OpenMetadata wildcard search first
        hits = self._search("*", limit)
        if hits:
            return [_parse_table(hit["_source"]) for hit in hits]

        # Fallback to Trino introspection
        if self._trino_client:
            return self._introspect_trino(limit)

        return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Execute one OpenMetadata search call and return raw hit list."""
        url = f"{self._base_url}{_SEARCH_PATH}"
        params = {"q": query, "index": _DEFAULT_INDEX, "size": limit}
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.get(url, params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.error("OpenMetadata connectivity error: %s", exc, exc_info=True)
            raise MetadataConnectivityError(
                f"Unable to reach OpenMetadata at {self._base_url}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "OpenMetadata HTTP error %s: %s", exc.response.status_code, exc
            )
            raise MetadataConnectivityError(
                f"OpenMetadata returned HTTP {exc.response.status_code}: {exc}"
            ) from exc

        return _extract_hits(response.json())

    def _introspect_trino(self, limit: int) -> list[TableMetadata]:
        """Discover tables directly from Trino's information_schema.

        Queries all catalogs' information_schema to find available tables
        and their columns.
        """
        if not self._trino_client:
            return []

        try:
            # Get tables from all catalogs
            tables_sql = (
                "SELECT table_catalog, table_schema, table_name "
                "FROM system.metadata.table_comments "
                f"LIMIT {limit}"
            )
            result = self._trino_client.execute(tables_sql, row_limit=limit)

            tables: list[TableMetadata] = []
            for row in result.rows:
                catalog = row.get("table_catalog", "")
                schema = row.get("table_schema", "")
                table_name = row.get("table_name", "")

                # Skip system schemas
                if schema in ("information_schema", "sys", "metadata"):
                    continue

                fqn = f"{catalog}.{schema}.{table_name}"

                # Get columns for this table
                columns = self._get_columns(catalog, schema, table_name)

                tables.append(TableMetadata(
                    fqn=fqn,
                    name=table_name,
                    description=None,
                    columns=columns,
                    tags=[],
                    relationships=[],
                ))

            logger.info("Introspected %d table(s) from Trino", len(tables))
            return tables

        except Exception as exc:
            logger.error("Trino introspection failed: %s", exc)
            return []

    def _get_columns(
        self, catalog: str, schema: str, table_name: str
    ) -> list[ColumnInfo]:
        """Get column information for a specific table from Trino."""
        if not self._trino_client:
            return []

        try:
            col_sql = (
                f"SELECT column_name, data_type "
                f"FROM {catalog}.information_schema.columns "
                f"WHERE table_schema = '{schema}' AND table_name = '{table_name}' "
                f"ORDER BY ordinal_position"
            )
            result = self._trino_client.execute(col_sql, row_limit=100)
            return [
                ColumnInfo(
                    name=row.get("column_name", ""),
                    data_type=row.get("data_type", ""),
                    description=None,
                )
                for row in result.rows
            ]
        except Exception as exc:
            logger.debug("Failed to get columns for %s.%s.%s: %s", catalog, schema, table_name, exc)
            return []


def _extract_hits(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull the list of hit documents from an OpenMetadata search response."""
    try:
        return data["hits"]["hits"]
    except (KeyError, TypeError):
        return []


def _parse_table(source: dict[str, Any]) -> TableMetadata:
    """Convert a raw ``_source`` document into a ``TableMetadata`` dataclass."""
    columns = [
        ColumnInfo(
            name=col.get("name", ""),
            data_type=col.get("dataType", ""),
            description=col.get("description") or None,
        )
        for col in source.get("columns", [])
    ]
    tags = [
        tag_obj["tagFQN"]
        for tag_obj in source.get("tags", [])
        if isinstance(tag_obj, dict) and tag_obj.get("tagFQN")
    ]

    # Extract a clean 3-part FQN for Trino from the OpenMetadata FQN
    # OM uses 4-part: service.database.schema.table
    # We need: catalog.schema.table (where catalog = the Trino catalog name)
    raw_fqn = source.get("fullyQualifiedName", "")
    fqn = _normalize_fqn(raw_fqn, source.get("name", ""))

    return TableMetadata(
        fqn=fqn,
        name=source.get("name", ""),
        description=source.get("description") or None,
        columns=columns,
        tags=tags,
        relationships=[],
    )


def _normalize_fqn(om_fqn: str, table_name: str) -> str:
    """Convert an OpenMetadata FQN to a Trino-compatible 3-part FQN.

    OpenMetadata uses: service_name.database.schema.table (4 parts)
    Trino needs:       catalog.schema.table (3 parts)

    Strategy:
    - If the FQN has exactly 3 dots (4 parts), take parts [1], [2], [3]
      as catalog (database), schema, table.
    - If it already has 3 parts, use as-is.
    - Otherwise, return the raw FQN.
    """
    parts = om_fqn.split(".")
    if len(parts) == 4:
        # service.database.schema.table → database.schema.table
        # The "database" in OM typically maps to the Trino catalog name
        # which is the datasource name configured in Polaris
        return f"{parts[1]}.{parts[2]}.{parts[3]}"
    elif len(parts) == 3:
        return om_fqn
    else:
        # Fallback — return as-is
        return om_fqn
