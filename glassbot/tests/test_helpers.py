"""
Unit tests for glassbot/utils/helpers.py.

Covers:
- count_tokens: token counting with tiktoken
- trim_conversation_history: trimming message lists to a token budget
- serialize_rows_for_log: compact JSON serialisation of query rows
- rows_to_dataframe: conversion of row dicts to a pandas DataFrame
- format_execution_time: formatting of execution times

Requirements: 7.2, 7.3
"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from glassbot.utils.helpers import (
    count_tokens,
    format_execution_time,
    rows_to_dataframe,
    serialize_rows_for_log,
    trim_conversation_history,
)


# ---------------------------------------------------------------------------
# count_tokens
# ---------------------------------------------------------------------------


class TestCountTokens:
    """count_tokens returns a non-negative integer for any string input."""

    def test_empty_string_returns_zero(self):
        assert count_tokens("") == 0

    def test_single_word(self):
        n = count_tokens("hello")
        assert isinstance(n, int)
        assert n > 0

    def test_longer_text_returns_more_tokens(self):
        short = count_tokens("hello")
        long = count_tokens("hello " * 100)
        assert long > short

    def test_known_model(self):
        # gpt-4o uses cl100k_base; "SELECT 1" is typically 2 tokens
        n = count_tokens("SELECT 1", model="gpt-4o")
        assert isinstance(n, int)
        assert n >= 1

    def test_fallback_for_unknown_model(self):
        # Should not raise; falls back to cl100k_base
        n = count_tokens("test", model="nonexistent-model-xyz")
        assert isinstance(n, int)
        assert n > 0

    def test_consistent_across_calls(self):
        text = "How many bottles were produced last month?"
        assert count_tokens(text) == count_tokens(text)


# ---------------------------------------------------------------------------
# trim_conversation_history
# ---------------------------------------------------------------------------


class TestTrimConversationHistory:
    """trim_conversation_history keeps messages within the token budget."""

    def _make_messages(self, n: int) -> list:
        """Create n human+AI turn pairs."""
        msgs = []
        for i in range(n):
            msgs.append(HumanMessage(content=f"Question {i}"))
            msgs.append(AIMessage(content=f"Answer {i}"))
        return msgs

    def test_empty_list_returns_empty(self):
        result = trim_conversation_history([], max_tokens=4000)
        assert result == []

    def test_short_history_unchanged(self):
        msgs = self._make_messages(2)  # 4 messages, tiny token count
        result = trim_conversation_history(msgs, max_tokens=4000)
        assert len(result) == len(msgs)

    def test_large_history_is_trimmed(self):
        # Create 100 turns — this should exceed a small token budget
        msgs = self._make_messages(100)
        result = trim_conversation_history(msgs, max_tokens=100)
        assert len(result) < len(msgs)

    def test_trimmed_result_is_list_of_base_messages(self):
        msgs = self._make_messages(5)
        result = trim_conversation_history(msgs, max_tokens=4000)
        from langchain_core.messages import BaseMessage
        assert all(isinstance(m, BaseMessage) for m in result)

    def test_system_message_is_preserved(self):
        """System messages must never be dropped by the trimmer."""
        system = SystemMessage(content="You are a Trino SQL expert.")
        human = HumanMessage(content="How many rows?")
        ai = AIMessage(content="SELECT count(*) FROM t")
        # Use a generous token budget so only keep the most recent + system
        result = trim_conversation_history([system, human, ai], max_tokens=4000)
        assert system in result


# ---------------------------------------------------------------------------
# serialize_rows_for_log
# ---------------------------------------------------------------------------


class TestSerializeRowsForLog:
    """serialize_rows_for_log produces compact, valid JSON strings."""

    def test_empty_list_returns_empty_json_array(self):
        assert serialize_rows_for_log([]) == "[]"

    def test_single_row(self):
        rows = [{"id": 1, "name": "bottle"}]
        result = serialize_rows_for_log(rows)
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["id"] == 1
        assert parsed[0]["name"] == "bottle"

    def test_truncates_at_max_rows(self):
        rows = [{"n": i} for i in range(20)]
        result = serialize_rows_for_log(rows, max_rows=10)
        parsed = json.loads(result)
        assert len(parsed) == 10

    def test_custom_max_rows(self):
        rows = [{"n": i} for i in range(5)]
        result = serialize_rows_for_log(rows, max_rows=3)
        parsed = json.loads(result)
        assert len(parsed) == 3

    def test_fewer_rows_than_max_included_entirely(self):
        rows = [{"n": i} for i in range(3)]
        result = serialize_rows_for_log(rows, max_rows=10)
        parsed = json.loads(result)
        assert len(parsed) == 3

    def test_non_json_serializable_values_become_strings(self):
        from datetime import datetime

        rows = [{"ts": datetime(2024, 1, 1, 12, 0, 0)}]
        # Should not raise; datetime serialised via default=str
        result = serialize_rows_for_log(rows)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "2024-01-01" in parsed[0]["ts"]

    def test_output_is_compact(self):
        rows = [{"a": 1}]
        result = serialize_rows_for_log(rows)
        # Compact separators — no space after ":" or ","
        assert " " not in result

    def test_preserves_row_order(self):
        rows = [{"n": i} for i in range(5)]
        result = serialize_rows_for_log(rows, max_rows=5)
        parsed = json.loads(result)
        assert [r["n"] for r in parsed] == list(range(5))


# ---------------------------------------------------------------------------
# rows_to_dataframe
# ---------------------------------------------------------------------------


class TestRowsToDataframe:
    """rows_to_dataframe converts row dicts to a pandas DataFrame."""

    def test_empty_rows_returns_empty_dataframe(self):
        df = rows_to_dataframe([])
        assert df.shape == (0, 0)

    def test_single_row(self):
        rows = [{"id": 1, "name": "bottle"}]
        df = rows_to_dataframe(rows)
        assert df.shape == (1, 2)
        assert list(df.columns) == ["id", "name"]
        assert df.iloc[0]["id"] == 1
        assert df.iloc[0]["name"] == "bottle"

    def test_multiple_rows(self):
        rows = [{"a": i, "b": i * 2} for i in range(5)]
        df = rows_to_dataframe(rows)
        assert df.shape == (5, 2)

    def test_columns_match_dict_keys(self):
        rows = [{"x": 1, "y": 2, "z": 3}]
        df = rows_to_dataframe(rows)
        assert set(df.columns) == {"x", "y", "z"}

    def test_returns_pandas_dataframe(self):
        import pandas as pd

        rows = [{"col": 42}]
        df = rows_to_dataframe(rows)
        assert isinstance(df, pd.DataFrame)


# ---------------------------------------------------------------------------
# format_execution_time
# ---------------------------------------------------------------------------


class TestFormatExecutionTime:
    """format_execution_time renders times in ms or s depending on magnitude."""

    # --- sub-second times rendered in ms ------------------------------------

    def test_zero_milliseconds(self):
        assert format_execution_time(0.0) == "0.00ms"

    def test_small_ms(self):
        assert format_execution_time(1.5) == "1.50ms"

    def test_two_decimal_places_ms(self):
        assert format_execution_time(42.567) == "42.57ms"

    def test_just_below_one_second(self):
        result = format_execution_time(999.99)
        assert result.endswith("ms")
        assert "999.99" in result

    # --- one second and over rendered in s ----------------------------------

    def test_exactly_one_second(self):
        assert format_execution_time(1000.0) == "1.00s"

    def test_one_and_a_half_seconds(self):
        assert format_execution_time(1500.0) == "1.50s"

    def test_large_time_in_seconds(self):
        result = format_execution_time(60000.0)
        assert result.endswith("s")
        assert "60.00" in result

    def test_two_decimal_places_s(self):
        result = format_execution_time(1234.5)
        assert result.endswith("s")
        assert "1.23" in result

    # --- threshold boundary -------------------------------------------------

    def test_boundary_999_99_is_ms(self):
        result = format_execution_time(999.99)
        assert "ms" in result

    def test_boundary_1000_is_s(self):
        result = format_execution_time(1000.0)
        assert result.endswith("s")
        assert "ms" not in result

    # --- output format ------------------------------------------------------

    def test_ms_suffix(self):
        result = format_execution_time(100.0)
        assert result.endswith("ms")

    def test_s_suffix(self):
        result = format_execution_time(2000.0)
        assert result.endswith("s")
        assert not result.endswith("ms")
