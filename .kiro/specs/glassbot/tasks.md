# Implementation Plan: GlassBot

## Overview

Build GlassBot end-to-end in Python, progressing from foundational infrastructure outward: configuration and logging first, then domain models and validators, then external-service clients (OpenMetadata, Trino), then LLM-facing components (SQL generation, response formatting), then the LangGraph agent orchestrator, then the Streamlit UI, and finally tests and deployment artifacts. Each task builds directly on the previous ones so no code is left unintegrated.

## Tasks

- [x] 1. Scaffold project structure and dependencies
  - Create the top-level directory layout: `glassbot/`, `glassbot/chatbot/`, `glassbot/utils/`, `glassbot/tests/`, `glassbot/tests/integration/`
  - Create all `__init__.py` files for every package
  - Write `glassbot/requirements.txt` with pinned versions for: `streamlit`, `langchain`, `langchain-core`, `langchain-community`, `langgraph`, `openai`, `anthropic`, `httpx`, `trino`, `sqlparse`, `python-dotenv`, `pydantic-settings`, `tiktoken`, `hypothesis`, `pytest`, `pytest-mock`
  - Write `glassbot/.env.example` listing all required and optional variables with placeholder values and inline descriptions
  - _Requirements: 11.1, 11.2, 11.4, 13.4_

- [x] 2. Implement configuration module (`config.py`)
  - Create `glassbot/config.py` reading all environment variables via `python-dotenv` / `pydantic-settings`
  - Define the `Config` class with every field listed in the design (`LLM_PROVIDER`, `OPENAI_API_KEY`, `TRINO_HOST`, `TRINO_PORT`, `TRINO_CATALOG`, `TRINO_SCHEMA`, `TRINO_USER`, `OPENMETADATA_URL`, `OPENMETADATA_API_TOKEN`, `LOG_LEVEL`, `LOG_FILE`, optional fields)
  - Raise `ConfigurationError` at import time for each missing required variable, including the variable name in the message
  - Define all domain exception classes in a shared `exceptions.py` or at the top of `config.py`: `GlassBotError`, `MetadataConnectivityError`, `MetadataNotFoundError`, `SQLValidationError`, `QueryExecutionError`, `LLMError`, `ConfigurationError`
  - _Requirements: 11.1, 11.2, 11.3_

  - [ ]* 2.1 Write property test for missing configuration variable error
    - **Property 11: Missing Configuration Variable Error**
    - **Validates: Requirements 11.3**

- [x] 3. Implement logging module (`utils/logger.py`)
  - Create `glassbot/utils/logger.py` with a `get_logger(component: str) -> logging.Logger` factory
  - Configure root logger once at startup with `StreamHandler` (stdout) and `FileHandler` (path from `config.LOG_FILE`), both using the format `%(asctime)s | %(levelname)s | %(name)s | %(message)s`
  - Read log level from `config.LOG_LEVEL`; default to `INFO`
  - Ensure calling `get_logger(__name__)` in any module returns a named child logger
  - _Requirements: 10.3, 10.4, 10.5_

- [x] 4. Implement domain data models
  - Create `glassbot/chatbot/models.py` (or inline in relevant modules) with `@dataclass` definitions for `ColumnInfo`, `TableMetadata`, `QueryResult`, and `ValidationResult` exactly as specified in the design
  - Define `AgentState` as a `TypedDict` in `glassbot/chatbot/agent.py` (stub file at this stage) with all fields from the design
  - _Requirements: 2.2, 5.3, 4.1_

- [x] 5. Implement SQL validator (`utils/validators.py`)
  - Create `glassbot/utils/validators.py` with `ALLOWLIST`, `BLOCKLIST`, and `SQLValidator.validate(sql: str) -> ValidationResult`
  - Implement the algorithm: strip leading whitespace/comments, call `sqlparse.parse()`, walk tokens to find the first `DML` or `Keyword` token (skipping whitespace/comments), normalise to uppercase, compare against allowlist/blocklist
  - Return `ValidationResult(is_valid=False, error_message="unparseable-SQL")` when the statement type cannot be determined
  - _Requirements: 4.1, 4.2, 4.4, 4.5_

  - [x] 5.1 Write unit tests for SQLValidator
    - Test acceptance of SELECT, WITH (CTE), EXPLAIN (case-insensitive, leading whitespace, inline comments)
    - Test rejection of DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE, CREATE
    - Test rejection of empty string and non-SQL text
    - _Requirements: 14.1_

  - [ ]* 5.2 Write property test for SQL validation allowlist
    - **Property 1: SQL Validation Allowlist**
    - **Validates: Requirements 4.1, 4.4**

  - [ ]* 5.3 Write property test for SQL validation blocklist
    - **Property 2: SQL Validation Blocklist**
    - **Validates: Requirements 4.1, 4.2**

- [x] 6. Implement helper utilities (`utils/helpers.py`)
  - Create `glassbot/utils/helpers.py` with: token-counting helper using `tiktoken`, `trim_messages` wrapper using `langchain_core.messages.trim_messages`, result-row serialisation for logging, and any table-rendering helpers needed by the UI
  - _Requirements: 7.2, 7.3_

- [x] 7. Implement MetadataService (`chatbot/metadata_service.py`)
  - Create `glassbot/chatbot/metadata_service.py` with `MetadataService` class
  - Implement `search_tables(self, question: str, limit: int = 5) -> list[TableMetadata]` using `httpx` to call `GET /api/v1/search/query?q={question}&index=table_search_index&size={limit}` on the configured OpenMetadata URL with the API token header
  - Parse the JSON response into `TableMetadata` / `ColumnInfo` dataclasses
  - Raise `MetadataNotFoundError` when the result list is empty; raise `MetadataConnectivityError` on `httpx.ConnectError` or network timeouts
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 7.1 Write unit tests for MetadataService
    - Mock HTTP response for successful search; verify `TableMetadata` fields populated correctly
    - Mock empty response; verify `MetadataNotFoundError` raised
    - Mock `httpx.ConnectError`; verify `MetadataConnectivityError` raised
    - _Requirements: 14.2_

  - [ ]* 7.2 Write property test for table metadata completeness
    - **Property 5: Table Metadata Completeness**
    - **Validates: Requirements 2.2, 3.2**

  - [ ]* 7.3 Write property test for metadata result limit
    - **Property 6: Metadata Result Limit**
    - **Validates: Requirements 2.5**

- [x] 8. Implement TrinoClient (`chatbot/trino_client.py`)
  - Create `glassbot/chatbot/trino_client.py` with `TrinoClient` class
  - Implement `execute(self, sql: str, row_limit: int = 1000) -> QueryResult` using `trino.dbapi.connect(host, port, user, catalog, schema)`
  - Wrap execution in `time.perf_counter()` for wall-clock timing in milliseconds
  - Fetch `row_limit + 1` rows; truncate to `row_limit` and set `truncated=True` / `truncation_limit=row_limit` if more than `row_limit` rows are returned
  - Catch `trino.exceptions.TrinoQueryError` and re-raise as `QueryExecutionError` with the Trino error message, without the internal stack trace
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 8.1 Write unit tests for TrinoClient
    - Test exactly 1000 rows: verify `truncated=False`, `row_count=1000`
    - Test 1001 rows returned: verify `truncated=True`, `len(rows)=1000`
    - Test Trino error: mock `TrinoQueryError` → verify `QueryExecutionError` raised with no raw stack trace
    - _Requirements: 14.1_

  - [ ]* 8.2 Write property test for row limit invariant
    - **Property 4: Row Limit Invariant**
    - **Validates: Requirements 5.3, 5.5**

- [x] 9. Checkpoint — core infrastructure complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement conversation memory (`chatbot/memory.py`)
  - Create `glassbot/chatbot/memory.py` with `ConversationMemory` class
  - Implement `add_turn(user_msg, assistant_msg, sql)`, `get_history() -> list[BaseMessage]`, and `clear()`
  - Store messages as `HumanMessage` / `AIMessage` pairs in an internal list; keep full list and trim only for LLM token-budget purposes using `trim_messages`
  - Document how `InMemorySaver` checkpointer keyed by `thread_id` is used by the LangGraph agent for multi-turn persistence (the in-process list is the local cache)
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 10.1 Write property test for conversation history retention and reset
    - **Property 10: Conversation History Retention and Reset**
    - **Validates: Requirements 7.3, 7.4**

- [x] 11. Implement prompt templates (`chatbot/prompts.py`)
  - Create `glassbot/chatbot/prompts.py` with:
    - `SYSTEM_PROMPT`: role definition, Trino SQL rules (fully qualified names, no `SELECT *`, explicit JOINs, default LIMIT), and output format (SQL only, no markdown fences)
    - `METADATA_TEMPLATE`: f-string/Jinja2 template rendering `TableMetadata` objects (name, description, columns with types and descriptions, tags, relationships) into the LLM context
    - `SUMMARY_PROMPT`: instructions for the ResponseFormatter LLM call
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 12. Implement SQLGenerator (`chatbot/sql_generator.py`)
  - Create `glassbot/chatbot/sql_generator.py` with `SQLGenerator` class
  - Constructor accepts `llm: BaseChatModel` and `prompts: PromptTemplates`; instantiate LLM via `langchain.chat_models.init_chat_model(config.LLM_PROVIDER)` in calling code
  - Implement `generate(question, metadata, history) -> str`: assemble system prompt, metadata block (using `METADATA_TEMPLATE`), trimmed conversation history, and user question; call the LLM; return the response string (strip markdown code fences if present)
  - Implement `_build_prompt(question, metadata_list, history) -> list[BaseMessage]` as a separate method for testability
  - Raise `LLMError` on API failure or timeout
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 12.1, 12.2, 12.3_

  - [ ]* 12.1 Write property test for prompt contains metadata context
    - **Property 12: Prompt Contains Metadata Context**
    - **Validates: Requirements 3.2, 3.5**

  - [ ]* 12.2 Write property test for generated SQL is a safe statement
    - **Property 3: Generated SQL is a Safe Statement**
    - **Validates: Requirements 3.1, 14.4**

- [x] 13. Implement ResponseFormatter (`chatbot/response_formatter.py`)
  - Create `glassbot/chatbot/response_formatter.py` with `ResponseFormatter` class
  - Implement `format(question: str, result: QueryResult) -> str`
  - If `result.row_count == 0`, return a canned "no data matched" message without an LLM call
  - Otherwise, call LLM with `SUMMARY_PROMPT`, the question, first 100 rows (to avoid token overflow), row count, and execution time; always include row count and execution time in the returned string
  - Raise `LLMError` on API failure
  - _Requirements: 6.1, 6.2, 6.3_

  - [x] 13.1 Write unit tests for ResponseFormatter
    - Non-empty result: mock LLM → verify summary contains row count and execution time
    - Empty result (`row_count=0`): verify canned message returned without LLM call
    - _Requirements: 14.3_

  - [ ]* 13.2 Write property test for response formatter summary invariants
    - **Property 9: Response Formatter Summary Invariants**
    - **Validates: Requirements 6.2, 6.3**

- [x] 14. Implement Executor (`chatbot/executor.py`)
  - Create `glassbot/chatbot/executor.py` as a thin coordinator wrapping `SQLValidator` and `TrinoClient`
  - Expose a single `execute(sql: str) -> QueryResult` method: validate first, then execute; raise `SQLValidationError` if validation fails (so the LangGraph node can catch it cleanly)
  - _Requirements: 4.2, 5.1_

- [x] 15. Implement LangGraph agent (`chatbot/agent.py`)
  - Complete `glassbot/chatbot/agent.py`: define `AgentState` TypedDict and build the `StateGraph`
  - Implement all six graph nodes as pure functions: `retrieve_metadata`, `generate_sql`, `validate_sql`, `execute_query`, `format_response`, `respond`
  - Each node catches its own exceptions, writes to `state["error"]` and `state["error_source"]`, and logs at ERROR level before setting the error field
  - Add conditional routing edges using `route_after_node(state)`: if `state["error"]` is set, route to `respond`; otherwise continue to the next node
  - Wire `InMemorySaver` checkpointer keyed by `thread_id` for multi-turn session persistence
  - Instantiate LLM via `init_chat_model(config.LLM_PROVIDER)` and inject into `SQLGenerator` and `ResponseFormatter`
  - _Requirements: 2.1, 2.3, 2.4, 3.1, 4.1, 4.2, 5.1, 6.1, 7.1, 7.2, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 10.1_

  - [ ]* 15.1 Write property test for no SQL on empty metadata
    - **Property 7: No SQL on Empty Metadata**
    - **Validates: Requirements 2.3, 8.1**

  - [ ]* 15.2 Write property test for rejected SQL is never executed
    - **Property 8: Rejected SQL is Never Executed**
    - **Validates: Requirements 4.2, 8.2**

- [x] 16. Checkpoint — agent pipeline complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Implement Streamlit UI (`app.py`)
  - Create `glassbot/app.py` as the Streamlit entry point
  - Initialise `st.session_state` with `messages` list and a UUID `thread_id`; instantiate the LangGraph agent once and store in session state
  - Render a chat input (`st.chat_input`) that accepts up to 2000 characters; show a validation message and do not forward empty submissions
  - Disable input and show `st.spinner` while the agent is running; re-enable on response
  - Display each chat turn using `st.chat_message`; render the natural language summary as the primary message body
  - Render the generated SQL in a `st.expander` labeled "Generated SQL" (collapsible code block)
  - Render the metadata summary in a `st.expander` labeled "Metadata Used" (collapsible)
  - Render the results table using `st.dataframe` with row count and execution time below; display truncation notice when `QueryResult.truncated=True`
  - Add a "Clear Conversation" button in the sidebar that resets `st.session_state.messages` and generates a new `thread_id`
  - Display all error messages in a visually distinct style (e.g., `st.error`)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.3, 6.4, 7.4, 8.6, 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 18. Write Hypothesis property-based test file (`tests/test_properties.py`)
  - Create `glassbot/tests/test_properties.py` with all 12 property tests from the design
  - Define Hypothesis strategies: `valid_sql_strategy`, `destructive_sql_strategy`, `table_metadata_strategy`, `question_strategy`, `valid_question_strategy`, `nonempty_query_result_strategy`, `execution_time_strategy`, `conversation_turn_strategy`
  - Each test is decorated with `@given(...)` and `@settings(max_examples=100)`; each includes the feature/property comment as shown in the design
  - Annotate each test with its property number and the requirements clause it validates
  - _Requirements: 14.4_

- [x] 19. Write integration test file (`tests/integration/test_integration.py`)
  - Create `glassbot/tests/integration/test_integration.py` marked with `@pytest.mark.integration` on every test
  - Test Trino connectivity: verify the glass bottle catalog is accessible
  - Test OpenMetadata search: verify that glass-bottle domain terms return table metadata
  - End-to-end smoke test: submit "How many bottles were produced last month?" and verify a non-empty response string
  - Ensure integration tests are excluded from the default `pytest` run via `pytest.ini` or `pyproject.toml` configuration
  - _Requirements: 5.1, 2.1_

- [x] 20. Write Docker deployment artifacts
  - Create `glassbot/Dockerfile` using `python:3.12-slim` as base: copy source, install `requirements.txt` with pinned versions, set `CMD ["streamlit", "run", "app.py", "--server.port=8501"]`
  - Create `glassbot/docker-compose.yml` defining the `glassbot` service: build from `./glassbot`, port `8501:8501`, `env_file: .env`
  - Create `glassbot/README.md` with setup instructions: prerequisites, how to copy `.env.example` to `.env` and fill in credentials, how to run with Docker Compose, how to run locally, and how to run the test suite
  - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [x] 21. Final checkpoint — all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints at tasks 9, 16, and 21 provide incremental validation gates
- Property tests validate the 12 universal correctness properties defined in the design; unit tests cover specific examples and boundary conditions
- Integration tests (task 19) require live Trino and OpenMetadata services and are excluded from the default pytest run
