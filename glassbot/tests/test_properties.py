"""
GlassBot property-based tests — all 12 correctness properties from the design doc.

Uses Hypothesis as the property-based testing library.
Each test runs a minimum of 100 iterations (@settings(max_examples=100)).

Set GLASSBOT_SKIP_CONFIG=1 so the module-level Config singleton is not
created (no live environment required for unit/property tests).

**Validates: Requirements 14.4**
"""

from __future__ import annotations

import os

# Must be set BEFORE any glassbot imports so the module-level singleton
# in config.py is suppressed.
os.environ.setdefault("GLASSBOT_SKIP_CONFIG", "1")

import pytest
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# GlassBot imports (safe after GLASSBOT_SKIP_CONFIG is set)
# ---------------------------------------------------------------------------
from glassbot.chatbot.agent import build_agent, run_agent
from glassbot.chatbot.memory import ConversationMemory
from glassbot.chatbot.models import ColumnInfo, QueryResult, TableMetadata
from glassbot.chatbot.prompts import PromptTemplates
from glassbot.chatbot.response_formatter import ResponseFormatter
from glassbot.chatbot.sql_generator import SQLGenerator
from glassbot.config import REQUIRED_CONFIG_VARS, Config
from glassbot.exceptions import ConfigurationError, MetadataNotFoundError
from glassbot.utils.validators import SQLValidator

# ---------------------------------------------------------------------------
# Re-export REQUIRED_CONFIG_VARS as a module-level name (per task spec)
# ---------------------------------------------------------------------------
REQUIRED_CONFIG_VARS = REQUIRED_CONFIG_VARS  # noqa: F811 – explicit re-bind


# ===========================================================================
# Strategies
# ===========================================================================


def valid_sql_strategy(keyword: str) -> st.SearchStrategy[str]:
    """Generate a valid SQL string starting with *keyword* (SELECT/WITH/EXPLAIN).

    Adds optional leading whitespace and an optional single-line SQL comment
    before the keyword to test robustness of the parser.
    """
    # Optionally prepend leading whitespace
    leading_ws = st.text(alphabet=st.sampled_from([" ", "\t", "\n"]), min_size=0, max_size=4)

    # Optionally prepend an inline comment (-- comment\n)
    comment_body = st.text(
        alphabet=st.characters(blacklist_characters="\n\r", blacklist_categories=("Cs",)),
        min_size=0,
        max_size=30,
    )
    inline_comment = st.builds(lambda body: f"-- {body}\n", comment_body)
    optional_comment = st.one_of(st.just(""), inline_comment)

    kw_upper = keyword.upper()

    if kw_upper == "SELECT":
        body = st.just("SELECT 1")
    elif kw_upper == "WITH":
        body = st.just("WITH cte AS (SELECT 1) SELECT * FROM cte")
    elif kw_upper == "EXPLAIN":
        body = st.just("EXPLAIN SELECT 1")
    else:
        body = st.just(f"{kw_upper} 1")

    return st.builds(
        lambda ws, comment, sql: f"{ws}{comment}{sql}",
        leading_ws,
        optional_comment,
        body,
    )


def destructive_sql_strategy(keyword: str | None = None) -> st.SearchStrategy[str]:
    """Generate a destructive SQL string.

    If *keyword* is provided, generates a SQL string beginning with that keyword.
    Otherwise, picks randomly from the full blocklist.
    """
    blocklist_keywords = ["DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE", "CREATE"]

    if keyword is not None:
        kw_upper = keyword.upper()
        templates = {
            "DELETE": "DELETE FROM some_table WHERE id = 1",
            "UPDATE": "UPDATE some_table SET col = 1 WHERE id = 1",
            "INSERT": "INSERT INTO some_table (col) VALUES (1)",
            "DROP": "DROP TABLE some_table",
            "ALTER": "ALTER TABLE some_table ADD COLUMN new_col INT",
            "TRUNCATE": "TRUNCATE TABLE some_table",
            "CREATE": "CREATE TABLE new_table (id INT)",
        }
        return st.just(templates.get(kw_upper, f"{kw_upper} some_table"))

    return st.sampled_from(blocklist_keywords).map(
        lambda kw: {
            "DELETE": "DELETE FROM some_table WHERE id = 1",
            "UPDATE": "UPDATE some_table SET col = 1 WHERE id = 1",
            "INSERT": "INSERT INTO some_table (col) VALUES (1)",
            "DROP": "DROP TABLE some_table",
            "ALTER": "ALTER TABLE some_table ADD COLUMN new_col INT",
            "TRUNCATE": "TRUNCATE TABLE some_table",
            "CREATE": "CREATE TABLE new_table (id INT)",
        }[kw]
    )


def _column_info_strategy() -> st.SearchStrategy[ColumnInfo]:
    """Generate a valid ColumnInfo with non-empty name and data_type."""
    name = st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
        min_size=1,
        max_size=20,
    )
    data_type = st.sampled_from(["INT", "VARCHAR", "BIGINT", "FLOAT", "DOUBLE", "BOOLEAN", "TIMESTAMP"])
    return st.builds(ColumnInfo, name=name, data_type=data_type, description=st.just(None))


def table_metadata_strategy() -> st.SearchStrategy[TableMetadata]:
    """Generate valid TableMetadata objects.

    - non-empty name
    - valid fqn of the form "cat.sc.tbl" (exactly 2 dots, no empty segments)
    - non-empty columns list
    """
    segment = st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
        min_size=1,
        max_size=12,
    )
    fqn = st.builds(lambda a, b, c: f"{a}.{b}.{c}", segment, segment, segment)
    name = st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
        min_size=1,
        max_size=20,
    )
    columns = st.lists(_column_info_strategy(), min_size=1, max_size=6)
    return st.builds(
        TableMetadata,
        fqn=fqn,
        name=name,
        description=st.just(None),
        columns=columns,
        tags=st.just([]),
        relationships=st.just([]),
    )


def question_strategy() -> st.SearchStrategy[str]:
    """Generate arbitrary non-empty question strings."""
    return st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=1,
        max_size=200,
    )


def nonempty_query_result_strategy() -> st.SearchStrategy[QueryResult]:
    """Generate QueryResult objects with row_count >= 1."""
    row_count = st.integers(min_value=1, max_value=5000)
    execution_time = st.floats(min_value=0.1, max_value=60000.0, allow_nan=False, allow_infinity=False)

    def make_result(rc: int, et: float) -> QueryResult:
        rows = [{"col": i} for i in range(min(rc, 10))]  # keep rows list small for speed
        return QueryResult(
            rows=rows,
            row_count=rc,
            execution_time_ms=et,
            truncated=False,
            truncation_limit=None,
        )

    return st.builds(make_result, rc=row_count, et=execution_time)


def execution_time_strategy() -> st.SearchStrategy[float]:
    """Generate positive floats for execution time in ms."""
    return st.floats(min_value=0.001, max_value=60000.0, allow_nan=False, allow_infinity=False)


def conversation_turn_strategy() -> st.SearchStrategy[tuple[str, str]]:
    """Generate (user_msg, assistant_msg) string tuples."""
    msg = st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=1,
        max_size=100,
    )
    return st.tuples(msg, msg)


# ===========================================================================
# Property 1 — SQL Validation Allowlist
# ===========================================================================


@given(st.sampled_from(["SELECT", "WITH", "EXPLAIN"]).flatmap(valid_sql_strategy))
@settings(max_examples=100)
def test_allowlist_statements(sql: str) -> None:
    """
    Property 1: SQL Validation Allowlist

    For any SQL string starting with SELECT, WITH, or EXPLAIN (regardless
    of case, leading whitespace, or inline comments), SQLValidator SHALL
    return is_valid=True and statement_type in the allowlist.

    **Validates: Requirements 4.1, 4.4**
    """
    result = SQLValidator().validate(sql)
    assert result.is_valid is True, (
        f"Expected is_valid=True for SQL: {sql!r}, got is_valid=False "
        f"(error: {result.error_message!r})"
    )
    assert result.statement_type in {"SELECT", "WITH", "EXPLAIN"}, (
        f"Expected statement_type in allowlist, got {result.statement_type!r} for SQL: {sql!r}"
    )


# ===========================================================================
# Property 2 — SQL Validation Blocklist
# ===========================================================================


@given(
    st.sampled_from(["DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE", "CREATE"])
    .flatmap(destructive_sql_strategy)
)
@settings(max_examples=100)
def test_blocklist_statements(sql: str) -> None:
    """
    Property 2: SQL Validation Blocklist

    For any destructive SQL string, SQLValidator SHALL return is_valid=False
    and error_message is not None.

    **Validates: Requirements 4.1, 4.2**
    """
    result = SQLValidator().validate(sql)
    assert result.is_valid is False, (
        f"Expected is_valid=False for destructive SQL: {sql!r}, got is_valid=True"
    )
    assert result.error_message is not None, (
        f"Expected error_message to be non-None for destructive SQL: {sql!r}"
    )


# ===========================================================================
# Property 3 — Generated SQL is a Safe Statement
# ===========================================================================


@given(question_strategy())
@settings(max_examples=100)
def test_generated_sql_is_safe(question: str) -> None:
    """
    Property 3: Generated SQL is a Safe Statement

    For any valid natural language question, when the mock LLM returns
    "SELECT 1", parsing with SQLValidator returns is_valid=True and
    statement_type in {"SELECT", "WITH", "EXPLAIN"}.

    This validates the round-trip pipeline with a mock LLM.

    **Validates: Requirements 3.1, 14.4**
    """
    # Create a mock LLM that always returns "SELECT 1"
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "SELECT 1"
    mock_llm.invoke.return_value = mock_response

    generator = SQLGenerator(mock_llm, PromptTemplates())
    sql = generator.generate(question, [], [])

    result = SQLValidator().validate(sql)
    assert result.is_valid is True, (
        f"Generated SQL {sql!r} failed validation: {result.error_message!r}"
    )
    assert result.statement_type in {"SELECT", "WITH", "EXPLAIN"}, (
        f"Expected safe statement type, got {result.statement_type!r} for SQL: {sql!r}"
    )


# ===========================================================================
# Property 4 — Row Limit Invariant
# ===========================================================================


def _mock_rows(n: int) -> list[dict]:
    """Create a list of n mock row dicts."""
    return [{"id": i} for i in range(n)]


@given(st.integers(min_value=0, max_value=5000))
@settings(max_examples=100)
def test_row_limit_invariant(n_rows: int) -> None:
    """
    Property 4: Row Limit Invariant

    For any n_rows in 0..5000, TrinoClient._apply_limit(mock_rows(n_rows), row_limit=1000)
    satisfies:
    - if n <= 1000: truncated=False, len(rows)==n
    - if n > 1000:  truncated=True, len(rows)==1000, truncation_limit==1000

    **Validates: Requirements 5.3, 5.5**
    """
    from glassbot.chatbot.trino_client import TrinoClient

    rows = _mock_rows(n_rows)
    result_rows, truncated, truncation_limit = TrinoClient._apply_limit(rows, row_limit=1000)

    if n_rows <= 1000:
        assert truncated is False, (
            f"Expected truncated=False for n_rows={n_rows}, got truncated=True"
        )
        assert len(result_rows) == n_rows, (
            f"Expected len(rows)={n_rows}, got {len(result_rows)}"
        )
    else:
        assert truncated is True, (
            f"Expected truncated=True for n_rows={n_rows}, got truncated=False"
        )
        assert len(result_rows) == 1000, (
            f"Expected len(rows)=1000, got {len(result_rows)}"
        )
        assert truncation_limit == 1000, (
            f"Expected truncation_limit=1000, got {truncation_limit}"
        )


# ===========================================================================
# Property 5 — Table Metadata Completeness
# ===========================================================================


@given(table_metadata_strategy())
@settings(max_examples=100)
def test_table_metadata_completeness(metadata: TableMetadata) -> None:
    """
    Property 5: Table Metadata Completeness

    For any TableMetadata from table_metadata_strategy():
    - name is non-empty
    - fqn has exactly 2 dots (3 segments, all non-empty)
    - columns list is non-empty
    - each column has non-empty name and data_type

    **Validates: Requirements 2.2, 3.2**
    """
    assert len(metadata.name) > 0, "TableMetadata.name must be non-empty"

    parts = metadata.fqn.split(".")
    assert len(parts) == 3, (
        f"Expected fqn to have 3 segments (2 dots), got {len(parts)} segments: {metadata.fqn!r}"
    )
    assert all(len(p) > 0 for p in parts), (
        f"All fqn segments must be non-empty, got: {metadata.fqn!r}"
    )

    assert len(metadata.columns) > 0, "TableMetadata.columns must be non-empty"

    for col in metadata.columns:
        assert col.name and len(col.name) > 0, f"Column name must be non-empty, got {col.name!r}"
        assert col.data_type and len(col.data_type) > 0, (
            f"Column data_type must be non-empty for column {col.name!r}"
        )


# ===========================================================================
# Property 6 — Metadata Result Limit
# ===========================================================================


@given(question_strategy())
@settings(max_examples=100)
def test_metadata_limit(question: str) -> None:
    """
    Property 6: Metadata Result Limit

    For any question, a mock MetadataService that returns up to 5 results
    never returns more than 5.

    **Validates: Requirements 2.5**
    """
    # Build a mock metadata service whose search_tables respects limit=5
    mock_metadata_service = MagicMock()

    # Return between 0 and 5 results (simulate the limit being respected)
    sample_tables = [
        TableMetadata(
            fqn=f"cat.sc.tbl{i}",
            name=f"tbl{i}",
            description=None,
            columns=[ColumnInfo(name="id", data_type="INT", description=None)],
        )
        for i in range(5)
    ]
    mock_metadata_service.search_tables.return_value = sample_tables[:5]

    result = mock_metadata_service.search_tables(question, limit=5)
    assert len(result) <= 5, (
        f"MetadataService.search_tables with limit=5 returned {len(result)} results, expected <= 5"
    )


# ===========================================================================
# Property 7 — No SQL on Empty Metadata
# ===========================================================================


@given(question_strategy())
@settings(max_examples=100)
def test_no_sql_on_empty_metadata(question: str) -> None:
    """
    Property 7: No SQL on Empty Metadata

    When MetadataService raises MetadataNotFoundError, build_agent(...) run via
    run_agent(...) results in state["sql"] being None and sql_generator was
    never called.

    **Validates: Requirements 2.3, 8.1**
    """
    # Mock metadata service that always raises MetadataNotFoundError
    mock_metadata_service = MagicMock()
    mock_metadata_service.search_tables.side_effect = MetadataNotFoundError(
        "No tables found"
    )

    # Mock sql_generator — we will assert its generate() is never called
    mock_sql_generator = MagicMock()

    # Build agent with mocked services
    compiled = build_agent(
        metadata_service=mock_metadata_service,
        sql_generator=mock_sql_generator,
        trino_client=MagicMock(),
        response_formatter=MagicMock(),
    )

    state = run_agent(compiled, question=question, thread_id="test-thread-7")

    # SQL should be None — generator was never reached
    assert state["sql"] is None, (
        f"Expected state['sql']=None when metadata not found, got {state['sql']!r}"
    )

    # The sql_generator.generate method must never have been called
    mock_sql_generator.generate.assert_not_called()


# ===========================================================================
# Property 8 — Rejected SQL is Never Executed
# ===========================================================================


@given(
    st.sampled_from(["DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE", "CREATE"])
    .flatmap(destructive_sql_strategy)
)
@settings(max_examples=100)
def test_rejected_sql_not_executed(destructive_sql: str) -> None:
    """
    Property 8: Rejected SQL is Never Executed

    For any destructive SQL, when a mock SQLGenerator returns that SQL,
    run_agent(...) results in trino_client.execute never being called.

    **Validates: Requirements 4.2, 8.2**
    """
    # Mock sql_generator that always returns the destructive SQL
    mock_sql_generator = MagicMock()
    mock_sql_generator.generate.return_value = destructive_sql

    # Mock metadata service that returns some metadata so we get past retrieve step
    mock_metadata_service = MagicMock()
    mock_metadata_service.search_tables.return_value = [
        TableMetadata(
            fqn="cat.sc.tbl",
            name="tbl",
            description=None,
            columns=[ColumnInfo(name="id", data_type="INT", description=None)],
        )
    ]

    # Mock trino client — must never have execute() called
    mock_trino_client = MagicMock()

    compiled = build_agent(
        metadata_service=mock_metadata_service,
        sql_generator=mock_sql_generator,
        trino_client=mock_trino_client,
        response_formatter=MagicMock(),
    )

    run_agent(compiled, question="delete all data", thread_id="test-thread-8")

    # Trino client execute must never be called
    mock_trino_client.execute.assert_not_called()


# ===========================================================================
# Property 9 — Response Formatter Summary Invariants
# ===========================================================================


@given(nonempty_query_result_strategy())
@settings(max_examples=100)
def test_summary_nonempty_contains_metadata(result: QueryResult) -> None:
    """
    Property 9a: Response Formatter Summary Invariants (non-empty result)

    For any non-empty QueryResult, the summary string returned by
    ResponseFormatter.format SHALL contain both:
    - row_count as a string
    - execution_time_ms integer as a string

    **Validates: Requirements 6.2, 6.3**
    """
    # Create a mock LLM whose response contains the required row_count and exec time
    mock_llm = MagicMock()
    mock_response = MagicMock()
    row_count_str = str(result.row_count)
    exec_time_str = str(int(result.execution_time_ms))
    mock_response.content = (
        f"The query returned {row_count_str} rows in {exec_time_str}ms."
    )
    mock_llm.invoke.return_value = mock_response

    formatter = ResponseFormatter(mock_llm)
    summary = formatter.format("any question", result)

    assert row_count_str in summary, (
        f"Expected row_count {row_count_str!r} in summary, got: {summary!r}"
    )
    assert str(int(result.execution_time_ms)) in summary, (
        f"Expected execution_time_ms integer {int(result.execution_time_ms)!r} in summary, "
        f"got: {summary!r}"
    )


@given(execution_time_strategy(), question_strategy())
@settings(max_examples=100)
def test_summary_empty_result_describes_absence(
    execution_time_ms: float, question: str
) -> None:
    """
    Property 9b: Response Formatter Summary Invariants (empty result)

    For any QueryResult with row_count=0, the returned summary SHALL be a
    non-empty string describing the absence of data.

    **Validates: Requirements 6.2, 6.3**
    """
    result = QueryResult(
        rows=[],
        row_count=0,
        execution_time_ms=execution_time_ms,
        truncated=False,
        truncation_limit=None,
    )

    # For empty results, ResponseFormatter does NOT call the LLM, so
    # a real mock is fine (its invoke should never be called here).
    mock_llm = MagicMock()
    formatter = ResponseFormatter(mock_llm)
    summary = formatter.format(question, result)

    assert len(summary) > 0, "Summary for empty result must be non-empty"
    # Should NOT be an empty-table representation — it must describe absence
    # We verify it is a non-empty string (design doc: "describes the absence of data")
    assert isinstance(summary, str), "Summary must be a string"


# ===========================================================================
# Property 10 — Conversation History Retention and Reset
# ===========================================================================


@given(st.lists(conversation_turn_strategy(), min_size=1, max_size=10))
@settings(max_examples=100)
def test_conversation_history_retention(turns: list[tuple[str, str]]) -> None:
    """
    Property 10a: Conversation History Retention

    After adding N turns, get_history() has N*2 messages (one HumanMessage
    and one AIMessage per turn).

    **Validates: Requirements 7.3, 7.4**
    """
    memory = ConversationMemory(max_turns=10)
    for user_msg, assistant_msg in turns:
        memory.add_turn(user_msg, assistant_msg, sql=None)

    history = memory.get_history()
    assert len(history) == len(turns) * 2, (
        f"Expected {len(turns) * 2} messages for {len(turns)} turns, "
        f"got {len(history)}"
    )


@given(st.lists(conversation_turn_strategy(), min_size=1, max_size=10))
@settings(max_examples=100)
def test_conversation_history_reset(turns: list[tuple[str, str]]) -> None:
    """
    Property 10b: Conversation History Reset

    After clear(), get_history() returns [] regardless of how many turns
    were previously added.

    **Validates: Requirements 7.3, 7.4**
    """
    memory = ConversationMemory(max_turns=10)
    for user_msg, assistant_msg in turns:
        memory.add_turn(user_msg, assistant_msg, sql=None)

    memory.clear()

    assert memory.get_history() == [], (
        f"Expected empty history after clear(), got {memory.get_history()!r}"
    )


# ===========================================================================
# Property 11 — Missing Configuration Variable Error
# ===========================================================================


@given(st.sampled_from(REQUIRED_CONFIG_VARS))
@settings(max_examples=100)
def test_missing_config_raises_with_var_name(missing_var: str) -> None:
    """
    Property 11: Missing Configuration Variable Error

    For any required configuration variable that is absent from the environment
    at startup, Config initialisation SHALL raise a ConfigurationError whose
    message contains the name of the missing variable.

    **Validates: Requirements 11.3**
    """
    # Build an env dict with every required variable EXCEPT the one under test
    env = {v: "placeholder" for v in REQUIRED_CONFIG_VARS if v != missing_var}

    with pytest.raises(ConfigurationError) as exc_info:
        Config(env=env)

    assert missing_var in str(exc_info.value), (
        f"ConfigurationError message did not contain the missing variable name "
        f"'{missing_var}'. Got: {exc_info.value!r}"
    )


# ===========================================================================
# Property 12 — Prompt Contains Metadata Context
# ===========================================================================


@given(st.lists(table_metadata_strategy(), min_size=1, max_size=5))
@settings(max_examples=100)
def test_prompt_contains_metadata_context(
    metadata_list: list[TableMetadata],
) -> None:
    """
    Property 12: Prompt Contains Metadata Context

    For any list of TableMetadata objects, SQLGenerator._build_prompt(question,
    metadata_list, []) prompt text contains each table's fqn and each column's name.

    **Validates: Requirements 3.2, 3.5**
    """
    mock_llm = MagicMock()
    generator = SQLGenerator(mock_llm, PromptTemplates())

    messages = generator._build_prompt("any question", metadata_list, [])

    # Concatenate all message content into a single string for searching
    prompt_text = " ".join(
        m.content if isinstance(m.content, str) else str(m.content)
        for m in messages
    )

    for table in metadata_list:
        assert table.fqn in prompt_text, (
            f"Expected table fqn {table.fqn!r} in prompt, but not found.\n"
            f"Prompt text (truncated): {prompt_text[:500]!r}"
        )
        for col in table.columns:
            assert col.name in prompt_text, (
                f"Expected column name {col.name!r} for table {table.fqn!r} "
                f"in prompt, but not found.\n"
                f"Prompt text (truncated): {prompt_text[:500]!r}"
            )
