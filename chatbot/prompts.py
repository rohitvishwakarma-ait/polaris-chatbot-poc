"""
Polaris prompt templates.

Builds LLM prompts dynamically from the table metadata returned by
OpenMetadata or Trino introspection — no hardcoded table schemas.

Contents:
- build_system_prompt: Dynamically constructs the SQL generation persona
  and rules from a list of TableMetadata objects.
- render_metadata: Renders TableMetadata objects into a structured context
  block for the LLM prompt.
- SUMMARY_PROMPT: Instructions for the ResponseFormatter LLM call.
- PromptTemplates: A dataclass grouping the above for injection into
  SQLGenerator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from chatbot.models import TableMetadata

# ---------------------------------------------------------------------------
# Core rules (schema-agnostic) — these never change regardless of data sources
# ---------------------------------------------------------------------------

_BASE_RULES: str = """\
RULES — follow every rule strictly:
1. Table names MUST use fully qualified names (catalog.schema.table) as shown above.
2. Pick the best-matching table(s) for the user's question based on the table descriptions.
3. Only use columns listed above — never invent column names.
4. If a column name contains spaces or reserved words, always double-quote it.
5. No SELECT * — select only needed columns.
6. Always include LIMIT (default 100) unless user asks for all rows.
7. Return ONLY the SQL — no explanation, no markdown fences, no trailing semicolon.

TYPE CASTING RULES — critical for avoiding errors:
8. When joining columns of different types (e.g., varchar to integer), always CAST explicitly.
9. varchar columns that hold dates should be compared as strings: WHERE col = '2026-07-08'
10. varchar columns that hold numbers should be CAST to integer/bigint for numeric operations.
11. Redis-style key-value tables (_key, _value) store JSON in _value — use LIKE for filtering.
"""


# ---------------------------------------------------------------------------
# Dynamic system prompt builder
# ---------------------------------------------------------------------------


def build_system_prompt(tables: list[TableMetadata]) -> str:
    """Build a complete system prompt dynamically from available table metadata.

    This replaces the previously hardcoded SYSTEM_PROMPT. The prompt includes:
    - A persona statement
    - The full schema listing derived from the provided TableMetadata
    - Universal SQL generation rules

    Args:
        tables: List of TableMetadata objects representing available tables.

    Returns:
        A complete system prompt string ready for the LLM.
    """
    if not tables:
        return (
            "You are a Trino SQL expert assistant.\n\n"
            "No table metadata is currently available. Ask the user to configure "
            "data sources in the Data Sources page first.\n\n"
            "If the user asks a question anyway, explain that no tables are "
            "configured and suggest they visit the Data Sources configuration page."
        )

    # Build the table listing
    table_blocks: list[str] = []
    for i, table in enumerate(tables, 1):
        block = f"Table {i}: {table.fqn}\n"
        block += f"Description: {table.description or '(no description)'}\n"
        block += "Columns:\n"
        for col in table.columns:
            desc = col.description or "(no description)"
            col_name = col.name
            # Quote column names with spaces
            if " " in col_name:
                col_name = f'"{col_name}"'
            block += f"  - {col_name} ({col.data_type}): {desc}\n"
        table_blocks.append(block)

    tables_text = "\n".join(table_blocks)

    return (
        "You are a Trino SQL expert assistant.\n\n"
        "The Trino instance contains the following tables. "
        "Use ONLY these exact fully qualified names (catalog.schema.table):\n\n"
        f"{tables_text}\n"
        f"{_BASE_RULES}"
    )


# ---------------------------------------------------------------------------
# Metadata template – renders TableMetadata objects into an LLM context block
# ---------------------------------------------------------------------------


def render_metadata(tables: list[TableMetadata]) -> str:
    """Render a list of TableMetadata objects into a structured string block.

    The returned string is intended to be injected as part of a system or
    human message so the LLM has full schema context for join generation.

    Args:
        tables: List of TableMetadata objects to render.

    Returns:
        A structured plain-text block describing each table.
    """
    if not tables:
        return "(No table metadata available.)"

    lines: list[str] = []
    for table in tables:
        lines.append(f"Table: {table.name}")
        lines.append(f"  Fully Qualified Name: {table.fqn}")
        lines.append(f"  Description: {table.description or '(no description)'}")

        if table.columns:
            lines.append("  Columns:")
            for col in table.columns:
                col_desc = col.description or "(no description)"
                lines.append(
                    f"    - {col.name} ({col.data_type}): {col_desc}"
                )
        else:
            lines.append("  Columns: (none)")

        if table.tags:
            lines.append(f"  Tags: {', '.join(table.tags)}")
        else:
            lines.append("  Tags: (none)")

        if table.relationships:
            lines.append("  Relationships:")
            for rel in table.relationships:
                lines.append(f"    - {rel}")
        else:
            lines.append("  Relationships: (none)")

        lines.append("")  # blank line between tables

    return "\n".join(lines).rstrip()


# Alias kept for backwards compatibility
METADATA_TEMPLATE = render_metadata

# ---------------------------------------------------------------------------
# Summary prompt – ResponseFormatter instructions (generic, not domain-specific)
# ---------------------------------------------------------------------------

SUMMARY_PROMPT: str = """\
You are a helpful data analyst assistant.

Summarise the following query results in plain English for a business user.
Always mention:
- The total number of rows returned.
- The query execution time in milliseconds.

Be concise and factual. Do not reproduce the raw data rows in your summary.
Highlight key patterns, totals, or insights where appropriate.
"""

# ---------------------------------------------------------------------------
# PromptTemplates – groups all templates for injection into SQLGenerator
# ---------------------------------------------------------------------------


@dataclass
class PromptTemplates:
    """Groups prompt strings and rendering helpers for SQLGenerator injection.

    Attributes:
        build_system_prompt: Callable that builds the system prompt from metadata.
        render_metadata: Callable that converts TableMetadata list to a string.
        summary_prompt: Instructions for the ResponseFormatter LLM call.
    """

    build_system_prompt: Callable = field(default=build_system_prompt)
    render_metadata: Callable = field(default=render_metadata)
    summary_prompt: str = SUMMARY_PROMPT
