"""
GlassBot SQL Generator.

Wraps LLM calls to produce Trino-compatible SQL from a user question,
table metadata context, and conversation history.

Public API:
  SQLGenerator(llm, prompts)
    .generate(question, metadata, history) -> str
    ._build_prompt(question, metadata_list, history) -> list[BaseMessage]
"""

from __future__ import annotations

import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from glassbot.chatbot.models import TableMetadata
from glassbot.chatbot.prompts import SYSTEM_PROMPT, PromptTemplates
from glassbot.exceptions import LLMError
from glassbot.utils.helpers import trim_conversation_history

# Regex to strip markdown SQL fences:  ```sql ... ``` or ``` ... ```
_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class SQLGenerator:
    """Generates Trino-compatible SQL from a natural language question.

    Args:
        llm: A provider-agnostic LangChain ``BaseChatModel`` instance.
        prompts: A ``PromptTemplates`` instance supplying the system prompt and
            metadata renderer.
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

        Builds the full prompt, calls the LLM, strips any markdown code fences
        from the response, and returns the clean SQL string.

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
          1. SystemMessage with the core SQL-generation persona and rules.
          2. SystemMessage with the rendered table metadata block.
          3. Trimmed conversation history (most recent turns kept).
          4. HumanMessage containing the user's question.

        Args:
            question: The user's natural language question.
            metadata_list: Table metadata objects to inject as schema context.
            history: Prior conversation messages (may be empty).

        Returns:
            An ordered list of :class:`~langchain_core.messages.BaseMessage`
            objects ready to be passed to the LLM.
        """
        messages: list[BaseMessage] = []

        # 1. Core SQL-generation persona with authoritative table list
        messages.append(SystemMessage(content=SYSTEM_PROMPT))

        # 2. Additional context from OpenMetadata (treat as supplementary only)
        # IMPORTANT: The system prompt's table list is authoritative.
        # Only use FQNs from the system prompt — never from this metadata block.
        metadata_text = self._prompts.render_metadata(metadata_list)
        messages.append(
            SystemMessage(content=(
                "Additional context from metadata catalog (for reference only):\n"
                f"{metadata_text}\n\n"
                "IMPORTANT: Ignore any FQNs shown above. "
                "Use ONLY the exact FQNs defined in your instructions above."
            ))
        )

        # 3. Trimmed conversation history
        trimmed_history = trim_conversation_history(history)
        messages.extend(trimmed_history)

        # 4. Current user question
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
