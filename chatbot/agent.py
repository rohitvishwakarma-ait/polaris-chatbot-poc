"""
GlassBot LangGraph agent orchestrator.

This module defines ``AgentState`` — the shared state TypedDict that flows
through every node of the LangGraph ``StateGraph`` — and builds the full
``StateGraph`` pipeline.

Graph topology:
    retrieve_metadata → generate_sql → validate_sql → execute_query →
    format_response → respond → END

Every non-terminal node has a conditional outgoing edge: if ``state["error"]``
is set the edge routes directly to ``respond``; otherwise it continues to the
next node in sequence.

Public API:
    AgentState         – TypedDict shared between all graph nodes
    build_agent(...)   – factory that wires services and returns a compiled graph
    run_agent(...)     – helper that invokes the compiled graph for one turn
"""

from __future__ import annotations

import functools
from typing import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph

from chatbot.executor import Executor
from chatbot.models import QueryResult, TableMetadata, ValidationResult
from utils.logger import get_logger
from utils.validators import SQLValidator

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    """
    Shared state passed between all nodes in the LangGraph StateGraph.

    Each node reads from and writes back to this dict.  Conditional routing
    edges inspect ``error`` after every node: if set, execution is routed
    directly to the ``respond`` node so that the user always receives a reply.

    Fields
    ------
    question:
        The raw natural language question submitted by the user.
    conversation_history:
        All previous ``BaseMessage`` objects in the current session,
        used to give the LLM multi-turn context.
    metadata:
        Table metadata retrieved from OpenMetadata; ``None`` until the
        ``retrieve_metadata`` node runs successfully.
    sql:
        The SQL string produced by the ``generate_sql`` node; ``None``
        until generation succeeds.
    validation_result:
        The ``ValidationResult`` produced by the ``validate_sql`` node;
        ``None`` until validation runs.
    query_result:
        The ``QueryResult`` returned by the ``execute_query`` node; ``None``
        until execution succeeds.
    summary:
        The natural language summary produced by the ``format_response`` node;
        ``None`` until formatting succeeds.
    error:
        A human-readable error message set by any node that catches an
        exception.  Presence of this field triggers routing to ``respond``.
    error_source:
        The name of the component that raised the error (used for logging
        and user-facing context).
    """

    question: str
    conversation_history: list[BaseMessage]
    metadata: list[TableMetadata] | None
    sql: str | None
    validation_result: ValidationResult | None
    query_result: QueryResult | None
    summary: str | None
    error: str | None
    error_source: str | None


# ---------------------------------------------------------------------------
# Graph node functions
# ---------------------------------------------------------------------------


def retrieve_metadata(state: AgentState, metadata_service) -> dict:
    """Fetch relevant table metadata from OpenMetadata.

    Calls ``metadata_service.search_tables(question)`` and writes the result
    to ``state["metadata"]``.  On any exception, writes a user-friendly
    message to ``state["error"]`` and sets ``state["error_source"]``.

    Args:
        state: Current agent state.
        metadata_service: An instance of ``MetadataService``.

    Returns:
        Dict update to merge into the agent state.
    """
    question = state["question"]
    try:
        metadata = metadata_service.search_tables(question)
        return {"metadata": metadata}
    except Exception as exc:
        logger.error(
            "MetadataService error while searching for question %r: %s",
            question,
            exc,
            exc_info=True,
        )
        return {
            "error": f"Could not retrieve table metadata: {exc}",
            "error_source": "MetadataService",
        }


def generate_sql(state: AgentState, sql_generator) -> dict:
    """Generate a Trino-compatible SQL query from the question and metadata.

    Calls ``sql_generator.generate(question, metadata, conversation_history)``
    and writes the result to ``state["sql"]``.

    Args:
        state: Current agent state.
        sql_generator: An instance of ``SQLGenerator``.

    Returns:
        Dict update to merge into the agent state.
    """
    question = state["question"]
    metadata = state.get("metadata") or []
    conversation_history = state.get("conversation_history") or []
    try:
        sql = sql_generator.generate(question, metadata, conversation_history)
        return {"sql": sql}
    except Exception as exc:
        logger.error(
            "SQLGenerator error for question %r: %s",
            question,
            exc,
            exc_info=True,
        )
        return {
            "error": f"Failed to generate SQL: {exc}",
            "error_source": "SQLGenerator",
        }


def validate_sql(state: AgentState) -> dict:
    """Validate the generated SQL against the safety allowlist/blocklist.

    Calls ``SQLValidator().validate(state["sql"])`` and writes the
    ``ValidationResult`` to ``state["validation_result"]``.  If validation
    fails (``is_valid == False``), also sets ``state["error"]`` and
    ``state["error_source"]``.

    Args:
        state: Current agent state.

    Returns:
        Dict update to merge into the agent state.
    """
    sql = state.get("sql") or ""
    validator = SQLValidator()
    validation_result = validator.validate(sql)
    if not validation_result.is_valid:
        error_msg = validation_result.error_message or "SQL validation failed."
        logger.error(
            "SQLValidator rejected SQL: %s | SQL: %r",
            error_msg,
            sql,
        )
        return {
            "validation_result": validation_result,
            "error": f"Query rejected: {error_msg}. No execution attempted.",
            "error_source": "SQLValidator",
        }
    return {"validation_result": validation_result}


def execute_query(state: AgentState, trino_client) -> dict:
    """Execute the validated SQL against Trino.

    Uses ``Executor(SQLValidator(), trino_client).execute(state["sql"])`` to
    perform a validate-then-execute step and writes the ``QueryResult`` to
    ``state["query_result"]``.

    Args:
        state: Current agent state.
        trino_client: An instance of ``TrinoClient``.

    Returns:
        Dict update to merge into the agent state.
    """
    sql = state.get("sql") or ""
    try:
        executor = Executor(SQLValidator(), trino_client)
        query_result = executor.execute(sql)
        return {"query_result": query_result}
    except Exception as exc:
        logger.error(
            "TrinoClient error executing SQL %r: %s",
            sql,
            exc,
            exc_info=True,
        )
        return {
            "error": f"Query execution failed: {exc}",
            "error_source": "TrinoClient",
        }


def format_response(state: AgentState, response_formatter) -> dict:
    """Format the query result as a natural language summary.

    Calls ``response_formatter.format(question, query_result)`` and writes the
    returned summary string to ``state["summary"]``.

    Args:
        state: Current agent state.
        response_formatter: An instance of ``ResponseFormatter``.

    Returns:
        Dict update to merge into the agent state.
    """
    question = state["question"]
    query_result = state.get("query_result")
    try:
        summary = response_formatter.format(question, query_result)
        return {"summary": summary}
    except Exception as exc:
        logger.error(
            "ResponseFormatter error for question %r: %s",
            question,
            exc,
            exc_info=True,
        )
        return {
            "error": f"Failed to format response: {exc}",
            "error_source": "ResponseFormatter",
        }


def respond(state: AgentState) -> dict:
    """Terminal node — passes the state through unchanged.

    This node is always the last to execute, whether the pipeline completed
    successfully or was short-circuited by an error in an earlier node.

    Args:
        state: Current agent state.

    Returns:
        Empty dict (no state updates needed; the node just marks the end).
    """
    # No mutations — just a named terminal node so routing can reference it.
    return {}


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------


def _route(state: AgentState, next_node: str) -> str:
    """Return *next_node* unless an error is set, in which case return "respond"."""
    if state.get("error"):
        return "respond"
    return next_node


def route_after_retrieve_metadata(state: AgentState) -> str:
    return _route(state, "generate_sql")


def route_after_generate_sql(state: AgentState) -> str:
    return _route(state, "validate_sql")


def route_after_validate_sql(state: AgentState) -> str:
    return _route(state, "execute_query")


def route_after_execute_query(state: AgentState) -> str:
    return _route(state, "format_response")


def route_after_format_response(state: AgentState) -> str:
    return _route(state, "respond")


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------


def _build_llm(config):
    """Instantiate the correct LLM backend based on config.LLM_PROVIDER.

    Supports:
    - ``cloudflare`` — CloudflareWorkersAI (custom adapter)
    - anything else  — delegated to ``langchain.chat_models.init_chat_model``
                       (supports openai, anthropic, azure_openai, ollama, etc.)

    Args:
        config: A ``Config`` instance.

    Returns:
        A ``BaseChatModel`` instance.
    """
    provider = (config.LLM_PROVIDER or "").lower().strip()

    if provider == "cloudflare":
        from chatbot.llm_cloudflare import CloudflareWorkersAI

        account_id = config.CLOUDFLARE_ACCOUNT_ID
        api_token = config.CLOUDFLARE_AIG_TOKEN
        model = config.CLOUDFLARE_MODEL

        if not account_id:
            raise RuntimeError(
                "CLOUDFLARE_ACCOUNT_ID is required when LLM_PROVIDER=cloudflare"
            )
        if not api_token:
            raise RuntimeError(
                "CLOUDFLARE_AIG_TOKEN is required when LLM_PROVIDER=cloudflare"
            )
        if not model:
            raise RuntimeError(
                "CLOUDFLARE_MODEL is required when LLM_PROVIDER=cloudflare "
                "(e.g. @cf/meta/llama-3.3-70b-instruct-fp8-fast)"
            )

        return CloudflareWorkersAI(
            account_id=account_id,
            api_token=api_token,
            model=model,
        )

    # All other providers go through LangChain's universal factory
    from langchain.chat_models import init_chat_model
    return init_chat_model(config.LLM_PROVIDER)


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------


def build_agent(
    config=None,
    metadata_service=None,
    sql_generator=None,
    trino_client=None,
    response_formatter=None,
):
    """Build and compile the LangGraph StateGraph for GlassBot.

    Instantiates the required services if they are not provided, then wires
    them into the graph nodes via ``functools.partial``.

    This function accepts service overrides for all dependencies so that tests
    can inject mocks without needing a real configuration object.

    Args:
        config: A ``Config`` instance.  Required when any service is ``None``
            and must be instantiated.
        metadata_service: Override for ``MetadataService``.
        sql_generator: Override for ``SQLGenerator``.
        trino_client: Override for ``TrinoClient``.
        response_formatter: Override for ``ResponseFormatter``.

    Returns:
        A compiled LangGraph ``StateGraph`` (``CompiledStateGraph``) ready to
        invoke via ``.invoke()`` or ``.stream()``.
    """
    # --- Instantiate services from config when overrides are not provided ---
    if metadata_service is None:
        from chatbot.metadata_service import MetadataService
        metadata_service = MetadataService(config)

    if trino_client is None:
        from chatbot.trino_client import TrinoClient
        trino_client = TrinoClient(config)

    if sql_generator is None or response_formatter is None:
        llm = _build_llm(config)

    if sql_generator is None:
        from chatbot.sql_generator import SQLGenerator
        from chatbot.prompts import PromptTemplates
        sql_generator = SQLGenerator(llm, PromptTemplates())

    if response_formatter is None:
        from chatbot.response_formatter import ResponseFormatter
        response_formatter = ResponseFormatter(llm)

    # --- Bind services into node functions via functools.partial ------------
    node_retrieve_metadata = functools.partial(
        retrieve_metadata, metadata_service=metadata_service
    )
    node_generate_sql = functools.partial(
        generate_sql, sql_generator=sql_generator
    )
    # validate_sql is a pure function — no service injection needed
    node_execute_query = functools.partial(
        execute_query, trino_client=trino_client
    )
    node_format_response = functools.partial(
        format_response, response_formatter=response_formatter
    )

    # --- Build the StateGraph -----------------------------------------------
    graph = StateGraph(AgentState)

    graph.add_node("retrieve_metadata", node_retrieve_metadata)
    graph.add_node("generate_sql", node_generate_sql)
    graph.add_node("validate_sql", validate_sql)
    graph.add_node("execute_query", node_execute_query)
    graph.add_node("format_response", node_format_response)
    graph.add_node("respond", respond)

    graph.set_entry_point("retrieve_metadata")

    graph.add_conditional_edges(
        "retrieve_metadata",
        route_after_retrieve_metadata,
        {"generate_sql": "generate_sql", "respond": "respond"},
    )
    graph.add_conditional_edges(
        "generate_sql",
        route_after_generate_sql,
        {"validate_sql": "validate_sql", "respond": "respond"},
    )
    graph.add_conditional_edges(
        "validate_sql",
        route_after_validate_sql,
        {"execute_query": "execute_query", "respond": "respond"},
    )
    graph.add_conditional_edges(
        "execute_query",
        route_after_execute_query,
        {"format_response": "format_response", "respond": "respond"},
    )
    graph.add_conditional_edges(
        "format_response",
        route_after_format_response,
        {"respond": "respond"},
    )

    # respond is the terminal node — route to END
    graph.add_edge("respond", END)

    # --- Compile the graph (no checkpointer) ---------------------------------
    # Conversation memory is managed externally via ConversationMemory and the
    # conversation_history field in AgentState.  Using MemorySaver caused
    # segfaults because LangGraph's checkpoint merge attempts to
    # serialize/deserialize the QueryResult and TableMetadata dataclasses
    # through pyarrow on subsequent invocations.
    compiled = graph.compile()
    return compiled


# ---------------------------------------------------------------------------
# Invocation helper
# ---------------------------------------------------------------------------


def run_agent(
    compiled_graph,
    question: str,
    thread_id: str,
    conversation_history: list[BaseMessage] | None = None,
) -> AgentState:
    """Invoke the compiled LangGraph agent for a single question.

    Args:
        compiled_graph: A compiled ``StateGraph`` returned by :func:`build_agent`.
        question: The user's natural language question.
        thread_id: A unique string identifying the current session.  Retained
            for API compatibility but no longer used for checkpointing.
        conversation_history: Prior conversation turns as LangChain
            ``BaseMessage`` objects.  Defaults to an empty list.

    Returns:
        The final ``AgentState`` dict after all graph nodes have executed.
    """
    initial_state: AgentState = {
        "question": question,
        "conversation_history": conversation_history or [],
        "metadata": None,
        "sql": None,
        "validation_result": None,
        "query_result": None,
        "summary": None,
        "error": None,
        "error_source": None,
    }
    return compiled_graph.invoke(initial_state)
