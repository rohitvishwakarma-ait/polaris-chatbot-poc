"""
Polaris Streamlit UI entry point.

This module is the top-level Streamlit application for Polaris — an AI-powered
analytics assistant that works with any data source configured via the
Data Sources page.

It:
- Initialises session state (message history, thread ID, compiled LangGraph agent)
- Renders the sidebar (title, description, "Clear Conversation" button)
- Renders the chat history (user and assistant messages with expandable SQL and metadata)
- Accepts user input via st.chat_input and drives the agent pipeline
- Displays query results (st.dataframe), generated SQL (st.expander), metadata
  used (st.expander), row counts, execution times, and truncation notices
- Handles ConfigurationError gracefully with a user-friendly st.error block

Run with::

    streamlit run app.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env from the root directory
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(os.path.join(_APP_DIR, ".env"))
except ImportError:
    pass  # python-dotenv not available; env vars must be set externally

import uuid
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call in the script
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Polaris", page_icon="⭐", layout="wide")

# ---------------------------------------------------------------------------
# Guard: attempt to import Config and catch ConfigurationError early so the
# UI can display a friendly error instead of crashing.
# ---------------------------------------------------------------------------
_CONFIG_ERROR: str | None = None
try:
    from config import Config
    from exceptions import ConfigurationError
    from chatbot.agent import build_agent, run_agent
    from utils.helpers import rows_to_dataframe, format_execution_time
except Exception as _import_exc:
    _CONFIG_ERROR = str(_import_exc)

    class ConfigurationError(Exception):  # type: ignore[no-redef]
        pass


# ---------------------------------------------------------------------------
# Helper: build a short metadata summary string for the "Metadata Used" expander
# ---------------------------------------------------------------------------


def _build_metadata_summary(metadata: list[Any] | None) -> str:
    """Return a brief human-readable string listing the table names/FQNs used."""
    if not metadata:
        return ""
    lines = []
    for table in metadata:
        fqn = getattr(table, "fqn", "")
        name = getattr(table, "name", "")
        if fqn and name and fqn != name:
            lines.append(f"{fqn} ({name})")
        elif fqn:
            lines.append(fqn)
        elif name:
            lines.append(name)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper: render a single assistant message dict
# ---------------------------------------------------------------------------


def _render_assistant_message(message: dict) -> None:
    """Render the content of one assistant message inside a st.chat_message block."""
    if message.get("error"):
        st.error(message["content"])
        return

    st.markdown(message["content"])

    sql = message.get("sql")
    if sql:
        with st.expander("Generated SQL"):
            st.code(sql, language="sql")

    metadata_summary = message.get("metadata_summary")
    if metadata_summary:
        with st.expander("Metadata Used"):
            st.text(metadata_summary)

    query_result = message.get("query_result")
    if query_result is not None:
        df = rows_to_dataframe(query_result.rows)
        st.dataframe(df)
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"Rows returned: **{query_result.row_count}**")
        with col2:
            st.caption(
                f"Execution time: **{format_execution_time(query_result.execution_time_ms)}**"
            )
        if query_result.truncated:
            st.info(
                f"Result truncated to {query_result.truncation_limit} rows. "
                "Refine your query to see more specific data."
            )


# ---------------------------------------------------------------------------
# Helper: parse final AgentState into an assistant message dict
# ---------------------------------------------------------------------------


def _state_to_assistant_message(state: dict) -> dict:
    """Convert a final AgentState dict into a chat message dict for storage."""
    error = state.get("error")
    if error:
        return {
            "role": "assistant",
            "content": error,
            "error": True,
        }

    summary = state.get("summary") or "I was unable to generate a response."
    sql = state.get("sql")
    metadata = state.get("metadata")
    query_result = state.get("query_result")

    msg: dict = {
        "role": "assistant",
        "content": summary,
    }
    if sql:
        msg["sql"] = sql
    if metadata:
        msg["metadata_summary"] = _build_metadata_summary(metadata)
    if query_result is not None:
        msg["query_result"] = query_result

    return msg


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------


def _init_session_state() -> None:
    """Initialise Streamlit session state keys if they are not yet set."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "agent" not in st.session_state:
        st.session_state.agent = None
        st.session_state.agent_error = None

        if _CONFIG_ERROR:
            st.session_state.agent_error = _CONFIG_ERROR
        else:
            try:
                cfg = Config()
                st.session_state.agent = build_agent(config=cfg)
            except ConfigurationError as exc:
                st.session_state.agent_error = str(exc)
            except Exception as exc:  # noqa: BLE001
                st.session_state.agent_error = (
                    f"Unexpected error initialising Polaris: {exc}"
                )


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the Streamlit application."""

    _init_session_state()

    # -----------------------------------------------------------------------
    # Sidebar
    # -----------------------------------------------------------------------
    with st.sidebar:
        st.title("⭐ Polaris")
        st.markdown(
            "Ask questions about your data in plain English. "
            "Polaris generates Trino SQL, executes it across your configured "
            "data sources, and explains the results."
        )
        st.divider()

        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()

        st.divider()
        st.caption("📌 Use the **Data Sources** page to add databases.")

    # -----------------------------------------------------------------------
    # Page title
    # -----------------------------------------------------------------------
    st.title("⭐ Polaris")
    st.caption("AI-powered analytics assistant — ask questions about any connected data source")

    # -----------------------------------------------------------------------
    # Show configuration error prominently and stop if the agent failed to build
    # -----------------------------------------------------------------------
    if st.session_state.get("agent_error"):
        st.error(
            "**Polaris could not start — configuration error**\n\n"
            f"{st.session_state.agent_error}\n\n"
            "**Setup instructions:**\n"
            "1. Copy `.env.example` to `.env` in the root directory.\n"
            "2. Fill in all required values: `LLM_PROVIDER`, `TRINO_HOST`, "
            "`OPENMETADATA_URL`, `OPENMETADATA_API_TOKEN`.\n"
            "3. Restart the Streamlit app."
        )
        st.stop()

    # -----------------------------------------------------------------------
    # Render existing chat history
    # -----------------------------------------------------------------------
    for message in st.session_state.messages:
        role = message.get("role", "user")
        with st.chat_message(role):
            if role == "assistant":
                _render_assistant_message(message)
            else:
                st.markdown(message.get("content", ""))

    # -----------------------------------------------------------------------
    # Chat input
    # -----------------------------------------------------------------------
    user_input: str | None = st.chat_input(
        "Ask a question about your data..."
    )

    if user_input is not None:
        question = user_input.strip()
        if not question:
            st.warning("Please enter a question.")
            st.stop()

        # Truncate at 2000 characters
        if len(question) > 2000:
            question = question[:2000]

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(question)

        # Run agent with spinner
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result_state = run_agent(
                        st.session_state.agent,
                        question,
                        st.session_state.thread_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    result_state = {
                        "error": (
                            f"An unexpected error occurred while processing your question: {exc}"
                        ),
                        "summary": None,
                        "sql": None,
                        "metadata": None,
                        "query_result": None,
                    }

            # Build and display the assistant message
            assistant_message = _state_to_assistant_message(result_state)
            _render_assistant_message(assistant_message)

        # Persist both messages to session state
        user_message = {"role": "user", "content": question}
        st.session_state.messages.append(user_message)
        st.session_state.messages.append(assistant_message)

        # Rerun to refresh the full chat display from session state
        st.rerun()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

main()
