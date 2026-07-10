"""
GlassBot ResponseFormatter.

Converts a QueryResult into a human-readable natural language summary using
an LLM.  For empty result sets (row_count == 0) a canned message is returned
immediately, without making any LLM API call.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from chatbot.models import QueryResult
from chatbot.prompts import SUMMARY_PROMPT
from exceptions import LLMError


class ResponseFormatter:
    """Formats query results as natural language summaries.

    Args:
        llm: A LangChain ``BaseChatModel`` instance (provider-agnostic).
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format(self, question: str, result: QueryResult) -> str:
        """Return a natural language summary of *result* for *question*.

        If ``result.row_count == 0`` a canned "no data" message is returned
        without calling the LLM.

        Otherwise the first 100 rows are passed to the LLM together with the
        original question, row count, and execution time so it can produce a
        concise, factual summary.  The returned string always contains the
        row count and execution time values.

        Args:
            question: The original natural language question from the user.
            result: The ``QueryResult`` produced by ``TrinoClient``.

        Returns:
            A natural language summary string.

        Raises:
            LLMError: When the underlying LLM API call raises any exception.
        """
        if result.row_count == 0:
            return (
                "No data matched the query conditions. "
                f"The query returned 0 rows in {result.execution_time_ms:.2f}ms."
            )

        # Truncate rows sent to the LLM to avoid token overflow
        rows_for_prompt = result.rows[:100]

        human_content = (
            f"User question: {question}\n\n"
            f"Row count: {result.row_count}\n"
            f"Execution time: {result.execution_time_ms:.2f}ms\n\n"
            f"Result rows (first {len(rows_for_prompt)}):\n{rows_for_prompt}"
        )

        messages = [
            SystemMessage(content=SUMMARY_PROMPT),
            HumanMessage(content=human_content),
        ]

        try:
            response = self._llm.invoke(messages)
        except Exception as exc:
            raise LLMError(f"LLM call failed in ResponseFormatter: {exc}") from exc

        summary: str = response.content if hasattr(response, "content") else str(response)

        # Guarantee the summary contains row_count and execution_time_ms
        # (the LLM is instructed to include them, but we add them as a
        # safety net in case the model omits them).
        row_count_str = str(result.row_count)
        exec_time_str = f"{result.execution_time_ms:.2f}ms"

        if row_count_str not in summary:
            summary = f"{summary}\n\nRows returned: {row_count_str}."

        if exec_time_str not in summary and str(int(result.execution_time_ms)) not in summary:
            summary = f"{summary} Execution time: {exec_time_str}."

        return summary
