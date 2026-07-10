"""
GlassBot helper utilities.

Provides miscellaneous helpers used across the application:

- ``count_tokens``             — count tokens in a string via ``tiktoken``
- ``trim_conversation_history`` — trim a message list to a token budget
- ``serialize_rows_for_log``   — compact JSON-like string for log output
- ``rows_to_dataframe``        — convert QueryResult rows to a pandas DataFrame
- ``format_execution_time``    — human-readable execution time string
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import tiktoken
from langchain_core.messages import BaseMessage, trim_messages

if TYPE_CHECKING:
    # pandas is imported lazily inside rows_to_dataframe to avoid making it a
    # hard dependency at module import time (it is only needed by the UI).
    import pandas as pd


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count the number of tokens in *text* for the given *model*.

    Uses ``tiktoken`` to obtain the correct encoding for the model.  Falls
    back to the ``cl100k_base`` encoding when the model name is not
    recognised by ``tiktoken``.

    Parameters
    ----------
    text:
        The string whose tokens should be counted.
    model:
        The model name used to select the tokeniser encoding, e.g.
        ``"gpt-4o"`` or ``"gpt-3.5-turbo"``.

    Returns
    -------
    int
        The number of tokens in *text* according to the model's tokeniser.
    """
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        # Unknown model — fall back to the most common encoding.
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


# ---------------------------------------------------------------------------
# Conversation history trimming
# ---------------------------------------------------------------------------


def trim_conversation_history(
    messages: list[BaseMessage],
    max_tokens: int = 4000,
    model: str = "gpt-4o",
) -> list[BaseMessage]:
    """Trim *messages* so that the total token count stays within *max_tokens*.

    Wraps ``langchain_core.messages.trim_messages`` with a ``tiktoken``-based
    token counter so that the result fits within the LLM context budget.

    The trimmer uses ``strategy="last"`` so the most recent messages are
    preserved and older messages are dropped first.  ``include_system=True``
    ensures system messages are never dropped.

    Parameters
    ----------
    messages:
        The full list of :class:`~langchain_core.messages.BaseMessage` objects
        to trim.
    max_tokens:
        The maximum total number of tokens that the trimmed list may contain.
    model:
        The model name used to select the tokeniser, e.g. ``"gpt-4o"``.

    Returns
    -------
    list[BaseMessage]
        A (possibly shorter) list of messages that fits within the token
        budget.  Returns *messages* unchanged when it already fits.
    """
    return trim_messages(
        messages,
        max_tokens=max_tokens,
        token_counter=lambda msgs: sum(
            count_tokens(m.content if isinstance(m.content, str) else str(m.content), model=model)
            for m in msgs
        ),
        strategy="last",
        include_system=True,
        allow_partial=False,
    )


# ---------------------------------------------------------------------------
# Result-row serialisation for logging
# ---------------------------------------------------------------------------


def serialize_rows_for_log(rows: list[dict], max_rows: int = 10) -> str:
    """Convert a sample of *rows* to a compact JSON-like string for logging.

    Only the first *max_rows* rows are included in the output to keep log
    entries readable.  Each row is serialised with ``json.dumps`` using
    ``default=str`` so that non-JSON-serialisable values (e.g. ``datetime``,
    ``Decimal``) are converted to their string representation without raising
    an exception.

    Parameters
    ----------
    rows:
        The full list of row dicts returned by a Trino query.
    max_rows:
        Maximum number of rows to include in the serialised output.
        Defaults to 10.

    Returns
    -------
    str
        A compact JSON array string containing up to *max_rows* rows, e.g.
        ``'[{"col": 1}, {"col": 2}]'``.  If *rows* is empty, returns
        ``"[]"``.
    """
    sample = rows[:max_rows]
    return json.dumps(sample, default=str, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Table rendering helpers (used by the Streamlit UI)
# ---------------------------------------------------------------------------


def rows_to_dataframe(rows: list[dict]) -> Any:
    """Convert a list of QueryResult row dicts to a pandas ``DataFrame``.

    pandas is imported *inside* this function to avoid creating a hard
    dependency at module import time.  The UI calls this helper when it needs
    to render results with ``st.dataframe``; other components (e.g. the agent
    pipeline) never import pandas.

    Parameters
    ----------
    rows:
        The ``rows`` attribute of a :class:`~glassbot.chatbot.models.QueryResult`.

    Returns
    -------
    pandas.DataFrame
        A ``DataFrame`` where each column corresponds to a key in the row
        dicts.  Returns an empty ``DataFrame`` when *rows* is empty.
    """
    import pandas  # noqa: PLC0415 — intentional lazy import

    return pandas.DataFrame(rows)


def format_execution_time(ms: float) -> str:
    """Format an execution time in milliseconds as a human-readable string.

    Renders times below one second as ``"X.XXms"`` and times of one second
    or more as ``"X.XXs"``.

    Parameters
    ----------
    ms:
        Execution time in milliseconds.

    Returns
    -------
    str
        A formatted string, e.g. ``"123.45ms"`` or ``"1.23s"``.

    Examples
    --------
    >>> format_execution_time(42.5)
    '42.50ms'
    >>> format_execution_time(1500.0)
    '1.50s'
    >>> format_execution_time(999.99)
    '999.99ms'
    >>> format_execution_time(1000.0)
    '1.00s'
    """
    if ms < 1000.0:
        return f"{ms:.2f}ms"
    return f"{ms / 1000.0:.2f}s"
