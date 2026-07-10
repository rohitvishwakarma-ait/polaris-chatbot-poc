"""
MetadataService — OpenMetadata integration for GlassBot.

Queries the OpenMetadata REST API to retrieve table metadata relevant to a
user question.

Key behaviour:
- Extracts short keyword tokens from the user question before searching,
  so that natural language phrases like "Give me completed production orders"
  become a focused query like "production orders" that OpenMetadata can match.
- When OpenMetadata returns no results for the extracted keywords, falls back
  to a broad search using each token individually.
- If all searches return empty, returns a hardcoded fallback set of the known
  glass-bottle business tables so the LLM always has schema context.

Error taxonomy:
    ``MetadataNotFoundError``  — raised when even the fallback returns nothing.
    ``MetadataConnectivityError`` — raised on network / HTTP connectivity failure.
"""

from __future__ import annotations

import logging
import re
from typing import Any

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

# Hardcoded fallback metadata for known glass-bottle tables.
# Used when OpenMetadata search returns no results so the LLM always
# has schema context.
_FALLBACK_TABLES: list[TableMetadata] = [
    TableMetadata(
        fqn="mysql.trino_glassbottle.customer_orders",
        name="customer_orders",
        description="Customer sales orders for glass bottle products",
        columns=[
            ColumnInfo("order_id", "integer", "Unique order identifier"),
            ColumnInfo("customer_name", "varchar", "Name of the customer"),
            ColumnInfo("order_number", "varchar", "Order reference number"),
            ColumnInfo("product_code", "varchar", "Glass bottle product code"),
            ColumnInfo("quantity", "integer", "Number of bottles ordered"),
            ColumnInfo("order_date", "date", "Date the order was placed"),
            ColumnInfo("delivery_date", "date", "Date the order was delivered"),
            ColumnInfo("status", "varchar",
                       "Order status: Delivered, Pending, Processing, Cancelled"),
        ],
        tags=["GlassBottle", "Sales"],
    ),
    TableMetadata(
        fqn="postgres.public.production_orders",
        name="production_orders",
        description="Internal production/manufacturing orders for glass bottles",
        columns=[
            ColumnInfo("production_id", "integer", "Unique production order identifier"),
            ColumnInfo("order_number", "varchar", "Order reference number"),
            ColumnInfo("product_code", "varchar", "Glass bottle product code"),
            ColumnInfo("quantity", "integer", "Number of bottles to produce"),
            ColumnInfo("machine_id", "varchar", "ID of the machine used"),
            ColumnInfo("shift", "varchar", "Work shift: Morning, Afternoon, Night"),
            ColumnInfo("production_date", "date", "Date of production"),
            ColumnInfo("status", "varchar",
                       "Production status: Completed, In Progress, Pending, Cancelled"),
        ],
        tags=["GlassBottle", "Production"],
    ),
    TableMetadata(
        fqn="mongodb.trino_glassbottle.machine_sensor_logs",
        name="machine_sensor_logs",
        description="Real-time machine sensor logs from glass bottle production equipment",
        columns=[
            ColumnInfo("machineid", "varchar", "Machine identifier"),
            ColumnInfo("productionid", "varchar", "Associated production order ID"),
            ColumnInfo("temperature", "bigint", "Machine temperature reading"),
            ColumnInfo("pressure", "bigint", "Machine pressure reading"),
            ColumnInfo("speed", "bigint", "Machine speed reading"),
            ColumnInfo("defects", "bigint", "Number of defects detected"),
            ColumnInfo("timestamp", "varchar", "Timestamp of the log entry"),
        ],
        tags=["GlassBottle", "MachineLogs"],
    ),
    TableMetadata(
        fqn="gsheets.default.trino_glassbottle_production_target",
        name="trino_glassbottle_production_target",
        description="Daily production targets from Google Sheets for glass bottle manufacturing",
        columns=[
            ColumnInfo("date", "varchar", "Production date"),
            ColumnInfo("product code", "varchar", "Glass bottle product code"),
            ColumnInfo("planned qty", "varchar", "Planned production quantity"),
            ColumnInfo("actual qty", "varchar", "Actual production quantity achieved"),
            ColumnInfo("supervisor", "varchar", "Supervisor name"),
            ColumnInfo("remarks", "varchar", "Additional remarks or notes"),
        ],
        tags=["GlassBottle", "ProductionTarget"],
    ),
    TableMetadata(
        fqn="redis.default.machine",
        name="machine",
        description="Real-time machine status from Redis cache (key-value format)",
        columns=[
            ColumnInfo("_key", "varchar", "Redis key"),
            ColumnInfo("_value", "varchar", "JSON value with machine status data"),
        ],
        tags=["GlassBottle", "Redis", "RealTime"],
    ),
    TableMetadata(
        fqn="redis.default.production",
        name="production",
        description="Live production counters and metrics from Redis cache (key-value format)",
        columns=[
            ColumnInfo("_key", "varchar", "Redis key"),
            ColumnInfo("_value", "varchar", "JSON value with production metrics"),
        ],
        tags=["GlassBottle", "Redis", "RealTime"],
    ),
    TableMetadata(
        fqn="redis.default.shift",
        name="shift",
        description="Current shift information from Redis cache (key-value format)",
        columns=[
            ColumnInfo("_key", "varchar", "Redis key"),
            ColumnInfo("_value", "varchar", "JSON value with shift details"),
        ],
        tags=["GlassBottle", "Redis", "RealTime"],
    ),
    TableMetadata(
        fqn="redis.default.dashboard",
        name="dashboard",
        description="Dashboard summary KPIs from Redis cache (key-value format)",
        columns=[
            ColumnInfo("_key", "varchar", "Redis key"),
            ColumnInfo("_value", "varchar", "JSON value with dashboard KPIs"),
        ],
        tags=["GlassBottle", "Redis", "RealTime"],
    ),
]




def _extract_keywords(question: str) -> str:
    """Extract meaningful keywords from a natural language question.

    Strips punctuation, lowercases, removes stop-words, and returns a
    space-separated string of the remaining tokens.  Falls back to the
    original question if nothing meaningful remains.

    Examples:
        "Give me completed production orders" → "completed production orders"
        "How many machines are running?"      → "machines running"
    """
    # Remove punctuation except spaces
    cleaned = re.sub(r"[^\w\s]", " ", question.lower())
    tokens = [t for t in cleaned.split() if t and t not in _STOP_WORDS and len(t) > 2]
    if not tokens:
        return question
    return " ".join(tokens)


class MetadataService:
    """Fetches table metadata from OpenMetadata via its REST search API."""

    def __init__(self, config: Any) -> None:
        self._base_url: str = config.OPENMETADATA_URL.rstrip("/")
        self._token: str = config.OPENMETADATA_API_TOKEN

    def search_tables(self, question: str, limit: int = 5) -> list[TableMetadata]:
        """Search OpenMetadata for tables relevant to *question*.

        Search strategy (in order):
        1. Search with extracted keywords from the question.
        2. If empty, search for each individual keyword token.
        3. If still empty, return the hardcoded fallback tables.

        Args:
            question: The user's natural language question.
            limit:    Maximum number of tables to return (default: 5).

        Returns:
            A list of ``TableMetadata`` objects (at most *limit* items).

        Raises:
            MetadataNotFoundError:     Only raised if fallback is also empty
                                       (should never happen in practice).
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

        # Attempt 3: hardcoded fallback
        if not hits:
            logger.warning(
                "No OpenMetadata results for %r — using hardcoded fallback tables",
                question,
            )
            return list(_FALLBACK_TABLES)

        tables = [_parse_table(hit["_source"]) for hit in hits]
        logger.debug("Found %d table(s) for question %r", len(tables), question)
        return tables

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
    return TableMetadata(
        fqn=source.get("fullyQualifiedName", ""),
        name=source.get("name", ""),
        description=source.get("description") or None,
        columns=columns,
        tags=tags,
        relationships=[],
    )
