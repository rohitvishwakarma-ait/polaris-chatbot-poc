"""
Polaris SQL Generator.

Wraps LLM calls to produce Trino-compatible SQL from a user question,
table metadata context, and conversation history.

The system prompt is now built dynamically from the metadata returned by
OpenMetadata / Trino introspection — no hardcoded table schemas.

Public API:
  SQLGenerator(llm, prompts)
    .generate(question, metadata, history) -> str
    ._build_prompt(question, metadata_list, history) -> list[BaseMessage]
"""

from __future__ import annotations

import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from chatbot.models import TableMetadata
from chatbot.prompts import PromptTemplates, build_system_prompt
from exceptions import LLMError
from utils.helpers import trim_conversation_history

# Regex to strip markdown SQL fences:  ```sql ... ``` or ``` ... ```
_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class SQLGenerator:
    """Generates Trino-compatible SQL from a natural language question.

    Args:
        llm: A provider-agnostic LangChain ``BaseChatModel`` instance.
        prompts: A ``PromptTemplates`` instance supplying the prompt builders.
    """

    def __init__(self, llm: BaseChatModel, prompts: PromptTemplates) -> None:
        self._llm = llm
        self._prompts = prompts

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(
        self,
        question: str,
        metadata: list[TableMetadata],
        history: list[BaseMessage],
    ) -> str:
        """Generate a SQL query for *question* given *metadata* and *history*.

        Builds the full prompt dynamically from the provided metadata, calls
        the LLM, strips any markdown code fences from the response, and
        returns the clean SQL string.

        Args:
            question: The user's natural language question.
            metadata: Table metadata objects retrieved from OpenMetadata.
            history: Prior conversation turns as LangChain message objects.

        Returns:
            A clean SQL string ready for validation and execution.

        Raises:
            LLMError: If the LLM call raises any exception.
        """
        messages = self._build_prompt(question, metadata, history)

        try:
            response = self._llm.invoke(messages)
        except Exception as exc:
            raise LLMError(f"LLM call failed: {exc}") from exc

        # Extract the text content from the response message.
        raw: str = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        return self._strip_fences(raw)

    # ------------------------------------------------------------------
    # Prompt construction (separated for testability)
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        question: str,
        metadata_list: list[TableMetadata],
        history: list[BaseMessage],
    ) -> list[BaseMessage]:
        """Assemble the ordered list of messages to send to the LLM.

        Message order:
          1. SystemMessage with the dynamically-built SQL-generation persona
             and table schema (derived from metadata_list).
          2. Trimmed conversation history (most recent turns kept).
          3. HumanMessage containing the user's question.

        The system prompt is built dynamically from the metadata — no
        hardcoded table schemas are used.

        Args:
            question: The user's natural language question.
            metadata_list: Table metadata objects to inject as schema context.
            history: Prior conversation messages (may be empty).

        Returns:
            An ordered list of BaseMessage objects ready for the LLM.
        """
        messages: list[BaseMessage] = []

        # 1. Dynamic system prompt built from the actual metadata
        system_prompt = self._prompts.build_system_prompt(metadata_list)
        messages.append(SystemMessage(content=system_prompt))

        # 2. Trimmed conversation history
        trimmed_history = trim_conversation_history(history)
        messages.extend(trimmed_history)

        # 3. Current user question
        messages.append(HumanMessage(content=question))

        return messages

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Remove markdown code fences (```sql ... ``` or ``` ... ```) if present.

        If the response is wrapped in fences, return only the content between
        them. Otherwise return the original text stripped of surrounding
        whitespace.

        Args:
            text: Raw LLM response string.

        Returns:
            Clean SQL string.
        """
        match = _FENCE_RE.search(text)
        if match:
            return match.group(1).strip()
        return text.strip()
