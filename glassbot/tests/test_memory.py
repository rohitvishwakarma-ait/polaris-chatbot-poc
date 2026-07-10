"""
Unit tests for ConversationMemory (chatbot/memory.py).

Covers:
- add_turn adds exactly 2 messages per turn (HumanMessage + AIMessage)
- get_history returns messages in insertion order
- Multiple turns are all retained
- clear resets to empty list
- get_history after clear returns empty list
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from chatbot.memory import ConversationMemory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_memory(max_turns: int = 10) -> ConversationMemory:
    return ConversationMemory(max_turns=max_turns)


# ---------------------------------------------------------------------------
# Tests: add_turn
# ---------------------------------------------------------------------------


def test_add_single_turn_produces_two_messages() -> None:
    """add_turn should append exactly one HumanMessage and one AIMessage."""
    mem = make_memory()
    mem.add_turn("Hello", "Hi there!", sql=None)
    history = mem.get_history()
    assert len(history) == 2


def test_add_single_turn_message_types() -> None:
    """First message is HumanMessage, second is AIMessage."""
    mem = make_memory()
    mem.add_turn("What is the total output?", "The total output is 1000 units.", sql=None)
    history = mem.get_history()
    assert isinstance(history[0], HumanMessage)
    assert isinstance(history[1], AIMessage)


def test_add_turn_with_sql_still_produces_two_messages() -> None:
    """Providing a SQL string should not add extra messages."""
    mem = make_memory()
    mem.add_turn("Show me production data", "Here are the results.", sql="SELECT * FROM production")
    assert len(mem.get_history()) == 2


def test_add_turn_message_content() -> None:
    """Message content matches the strings passed to add_turn."""
    mem = make_memory()
    user_text = "How many bottles were produced?"
    asst_text = "1,234 bottles were produced last month."
    mem.add_turn(user_text, asst_text, sql=None)
    history = mem.get_history()
    assert history[0].content == user_text
    assert history[1].content == asst_text


# ---------------------------------------------------------------------------
# Tests: multiple turns retention
# ---------------------------------------------------------------------------


def test_multiple_turns_all_retained() -> None:
    """Every turn added should appear in history—no turns are dropped."""
    mem = make_memory()
    turns = [
        ("Question 1", "Answer 1"),
        ("Question 2", "Answer 2"),
        ("Question 3", "Answer 3"),
    ]
    for user_msg, asst_msg in turns:
        mem.add_turn(user_msg, asst_msg, sql=None)

    history = mem.get_history()
    assert len(history) == len(turns) * 2


def test_ten_turns_all_retained() -> None:
    """All 10 minimum-retention turns must be present per Requirement 7.3."""
    mem = make_memory(max_turns=10)
    for i in range(10):
        mem.add_turn(f"User message {i}", f"Assistant reply {i}", sql=None)
    assert len(mem.get_history()) == 20


def test_more_than_max_turns_still_retained() -> None:
    """Turns beyond max_turns are kept (max_turns is only a minimum guarantee)."""
    mem = make_memory(max_turns=5)
    for i in range(15):
        mem.add_turn(f"Q {i}", f"A {i}", sql=None)
    assert len(mem.get_history()) == 30


# ---------------------------------------------------------------------------
# Tests: insertion order
# ---------------------------------------------------------------------------


def test_get_history_returns_messages_in_insertion_order() -> None:
    """Messages should appear in the order they were added."""
    mem = make_memory()
    mem.add_turn("First user", "First assistant", sql=None)
    mem.add_turn("Second user", "Second assistant", sql=None)
    mem.add_turn("Third user", "Third assistant", sql=None)

    history = mem.get_history()
    assert history[0].content == "First user"
    assert history[1].content == "First assistant"
    assert history[2].content == "Second user"
    assert history[3].content == "Second assistant"
    assert history[4].content == "Third user"
    assert history[5].content == "Third assistant"


# ---------------------------------------------------------------------------
# Tests: clear
# ---------------------------------------------------------------------------


def test_clear_resets_to_empty_list() -> None:
    """After clear(), get_history() should return an empty list."""
    mem = make_memory()
    mem.add_turn("Hello", "Hi", sql=None)
    mem.add_turn("Follow-up", "Sure", sql=None)
    mem.clear()
    assert mem.get_history() == []


def test_get_history_after_clear_returns_empty() -> None:
    """get_history() is idempotent after clear—multiple calls all return []."""
    mem = make_memory()
    mem.add_turn("Q", "A", sql=None)
    mem.clear()
    assert mem.get_history() == []
    assert mem.get_history() == []


def test_clear_on_empty_memory_is_safe() -> None:
    """Calling clear() on a freshly created memory should not raise."""
    mem = make_memory()
    mem.clear()
    assert mem.get_history() == []


def test_add_after_clear_works_correctly() -> None:
    """After clear(), new turns should be retained normally."""
    mem = make_memory()
    mem.add_turn("Old question", "Old answer", sql=None)
    mem.clear()
    mem.add_turn("New question", "New answer", sql=None)
    history = mem.get_history()
    assert len(history) == 2
    assert history[0].content == "New question"
    assert history[1].content == "New answer"


# ---------------------------------------------------------------------------
# Tests: default max_turns value
# ---------------------------------------------------------------------------


def test_default_max_turns_is_ten() -> None:
    """ConversationMemory() with no arguments should have max_turns=10."""
    mem = ConversationMemory()
    assert mem.max_turns == 10


def test_custom_max_turns_is_stored() -> None:
    """max_turns passed to __init__ should be accessible as an attribute."""
    mem = ConversationMemory(max_turns=25)
    assert mem.max_turns == 25
