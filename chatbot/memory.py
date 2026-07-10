"""
GlassBot conversation memory.

Provides ``ConversationMemory``, a simple in-memory store that accumulates
``HumanMessage`` / ``AIMessage`` pairs as conversation turns progress.

Token-based trimming for LLM calls is handled separately by
``trim_conversation_history`` in ``utils/helpers.py``.  This class is
responsible only for storing and returning the full message history.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class ConversationMemory:
    """Retain conversation history as a flat list of LangChain messages.

    Each call to :meth:`add_turn` appends one :class:`HumanMessage` and one
    :class:`AIMessage` to the internal list.  The list is never trimmed here;
    callers that need to stay within an LLM token budget should pass the
    result of :meth:`get_history` through
    ``utils.helpers.trim_conversation_history`` before building the prompt.

    Parameters
    ----------
    max_turns:
        Documents the minimum retention guarantee (Requirement 7.3).  The
        class always retains *all* turns; ``max_turns`` is not used to limit
        storage.  Default is ``10``.
    """

    def __init__(self, max_turns: int = 10) -> None:
        self.max_turns = max_turns
        self._messages: list[BaseMessage] = []

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_turn(
        self,
        user_msg: str,
        assistant_msg: str,
        sql: str | None,
    ) -> None:
        """Append one conversation turn to the history.

        A single turn consists of a :class:`HumanMessage` (the user's
        question) followed by an :class:`AIMessage` (the assistant's
        response).  The optional *sql* parameter is accepted for API
        compatibility but is not stored separately—it is part of the
        assistant message context that the caller may choose to embed in
        *assistant_msg* before calling this method.

        Parameters
        ----------
        user_msg:
            The raw question text entered by the user.
        assistant_msg:
            The natural language summary or response produced by the agent.
        sql:
            The SQL generated for this turn, or ``None`` if no SQL was
            produced (e.g. error path).  Stored for completeness; callers
            may embed it in *assistant_msg* if they wish it to appear in
            the LLM context.
        """
        self._messages.append(HumanMessage(content=user_msg))
        self._messages.append(AIMessage(content=assistant_msg))

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_history(self) -> list[BaseMessage]:
        """Return all stored messages in insertion order.

        Returns
        -------
        list[BaseMessage]
            A copy-by-reference list of :class:`~langchain_core.messages.BaseMessage`
            objects.  Each pair of consecutive messages corresponds to one
            conversation turn (``HumanMessage`` at even indices,
            ``AIMessage`` at odd indices).
        """
        return list(self._messages)

    def clear(self) -> None:
        """Reset the message list to empty.

        After this call :meth:`get_history` returns ``[]``.
        """
        self._messages = []
