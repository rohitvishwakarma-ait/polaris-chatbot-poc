"""
Unit tests for ResponseFormatter.

Tests cover:
- Non-empty result: mock LLM → summary contains row count and execution time
- Empty result (row_count=0): canned message returned WITHOUT calling the LLM
- Canned empty message contains execution time
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from chatbot.models import QueryResult
from chatbot.response_formatter import ResponseFormatter
from exceptions import LLMError


def _make_result(
    row_count: int,
    execution_time_ms: float = 123.45,
    rows: list | None = None,
    truncated: bool = False,
) -> QueryResult:
    """Helper to build a QueryResult for testing."""
    if rows is None:
        rows = [{"col": f"val{i}"} for i in range(row_count)]
    return QueryResult(
        rows=rows,
        row_count=row_count,
        execution_time_ms=execution_time_ms,
        truncated=truncated,
        truncation_limit=1000 if truncated else None,
    )


def _make_llm(response_text: str) -> MagicMock:
    """Build a MagicMock LLM whose invoke() returns a message-like object."""
    mock_response = MagicMock()
    mock_response.content = response_text
    llm = MagicMock()
    llm.invoke.return_value = mock_response
    return llm


class TestResponseFormatterNonEmpty(unittest.TestCase):
    """ResponseFormatter.format with non-empty QueryResult."""

    def test_summary_contains_row_count(self):
        """Summary must include the numeric row count from the result."""
        result = _make_result(row_count=42, execution_time_ms=200.0)
        llm = _make_llm(
            "The query returned 42 rows in 200.00ms covering production data."
        )
        formatter = ResponseFormatter(llm)

        summary = formatter.format("How many bottles?", result)

        self.assertIn("42", summary)

    def test_summary_contains_execution_time(self):
        """Summary must include the execution time value from the result."""
        result = _make_result(row_count=10, execution_time_ms=99.50)
        llm = _make_llm(
            "The query returned 10 rows. Execution time was 99.50ms."
        )
        formatter = ResponseFormatter(llm)

        summary = formatter.format("List products", result)

        # Accept either the formatted float string or the integer portion
        self.assertTrue(
            "99.50ms" in summary or "99" in summary,
            msg=f"Execution time not found in summary: {summary!r}",
        )

    def test_llm_invoke_is_called_for_non_empty_result(self):
        """The LLM must be called exactly once for a non-empty result."""
        result = _make_result(row_count=5, execution_time_ms=50.0)
        llm = _make_llm("5 rows returned in 50.00ms.")
        formatter = ResponseFormatter(llm)

        formatter.format("Show data", result)

        llm.invoke.assert_called_once()

    def test_summary_appends_row_count_when_llm_omits_it(self):
        """If the LLM summary omits the row count, formatter appends it."""
        result = _make_result(row_count=7, execution_time_ms=30.0)
        # LLM response deliberately missing the row count
        llm = _make_llm("Here is a summary of production data. Execution time: 30.00ms.")
        formatter = ResponseFormatter(llm)

        summary = formatter.format("Show data", result)

        self.assertIn("7", summary)

    def test_summary_appends_execution_time_when_llm_omits_it(self):
        """If the LLM summary omits the execution time, formatter appends it."""
        result = _make_result(row_count=3, execution_time_ms=45.67)
        # LLM response deliberately missing the execution time
        llm = _make_llm("The query returned 3 rows of production data.")
        formatter = ResponseFormatter(llm)

        summary = formatter.format("Show data", result)

        # Either the formatted value or integer portion should appear
        self.assertTrue(
            "45.67ms" in summary or "45" in summary,
            msg=f"Execution time not found in summary: {summary!r}",
        )

    def test_lm_error_raised_on_exception(self):
        """LLMError must be raised when the LLM.invoke() raises any exception."""
        result = _make_result(row_count=1, execution_time_ms=10.0)
        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("API timeout")
        formatter = ResponseFormatter(llm)

        with self.assertRaises(LLMError):
            formatter.format("What happened?", result)


class TestResponseFormatterEmptyResult(unittest.TestCase):
    """ResponseFormatter.format with empty QueryResult (row_count == 0)."""

    def test_returns_canned_message_for_zero_rows(self):
        """A canned 'no data' message must be returned for an empty result."""
        result = _make_result(row_count=0, execution_time_ms=5.0)
        llm = MagicMock()
        formatter = ResponseFormatter(llm)

        summary = formatter.format("Any question", result)

        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)

    def test_llm_is_not_called_for_empty_result(self):
        """The LLM must NOT be called when row_count is 0."""
        result = _make_result(row_count=0, execution_time_ms=12.34)
        llm = MagicMock()
        formatter = ResponseFormatter(llm)

        formatter.format("Any question", result)

        llm.invoke.assert_not_called()

    def test_canned_message_contains_execution_time(self):
        """The canned empty-result message must include the execution time."""
        execution_time_ms = 77.89
        result = _make_result(row_count=0, execution_time_ms=execution_time_ms)
        llm = MagicMock()
        formatter = ResponseFormatter(llm)

        summary = formatter.format("Any question", result)

        # The formatted execution time should appear in the message
        self.assertIn(f"{execution_time_ms:.2f}ms", summary)

    def test_canned_message_mentions_zero_rows(self):
        """The canned message must describe the absence of data (0 rows)."""
        result = _make_result(row_count=0, execution_time_ms=3.0)
        llm = MagicMock()
        formatter = ResponseFormatter(llm)

        summary = formatter.format("Any question", result)

        self.assertIn("0", summary)

    def test_canned_message_mentions_no_data(self):
        """The canned message should clearly communicate no data was found."""
        result = _make_result(row_count=0, execution_time_ms=1.0)
        llm = MagicMock()
        formatter = ResponseFormatter(llm)

        summary = formatter.format("Any question", result)

        summary_lower = summary.lower()
        self.assertTrue(
            "no data" in summary_lower or "0 rows" in summary_lower,
            msg=f"Expected 'no data' or '0 rows' in: {summary!r}",
        )


if __name__ == "__main__":
    unittest.main()
