# Requirements Document

## Introduction

GlassBot is an AI-powered chatbot for the Glass Bottle Manufacturing domain. It accepts natural language questions from users, retrieves business context from OpenMetadata, generates and validates Trino-compatible SQL, executes the query, and returns results in natural language. The system demonstrates Ontology-driven querying similar to Palantir Foundry, using a LangGraph/LangChain agent backend and a Streamlit frontend.

The chatbot connects to an existing Trino instance that holds a Glass Bottle Manufacturing sample database, and to an existing OpenMetadata instance that has ingested the Trino catalog metadata.

---

## Glossary

- **GlassBot**: The AI chatbot system described in this document.
- **Agent**: The LangGraph-based orchestration component that coordinates all sub-tasks (metadata retrieval, SQL generation, execution, response formatting).
- **LLM**: Large Language Model (initially OpenAI GPT-4); abstracted so that providers can be swapped without changing Agent logic.
- **MetadataService**: The component that queries OpenMetadata via REST API or Python SDK to retrieve table descriptions, column names, relationships, and tags.
- **SQLGenerator**: The component that constructs a Trino-compatible SQL query using the retrieved metadata and the user's question as LLM context.
- **SQLValidator**: The component that inspects a generated SQL string for syntax correctness and prohibited statement types before execution.
- **TrinoClient**: The component that manages the connection to Trino and executes read-only SQL queries.
- **ResponseFormatter**: The component that converts raw query results and metadata into a human-readable natural language summary.
- **ConversationMemory**: The component that retains conversation history within a session to support follow-up questions.
- **UI**: The Streamlit-based web frontend through which the user interacts with GlassBot.
- **Destructive Statement**: Any SQL statement of type DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE, or CREATE.
- **Safe Statement**: Any SQL statement of type SELECT, WITH (CTE), or EXPLAIN.
- **Session**: A single continuous interaction between a user and GlassBot, from first message to conversation clear or browser close.
- **QueryResult**: The structured object containing the result rows, row count, and execution time returned by the TrinoClient.
- **Fully Qualified Table Name**: A table reference in the form `catalog.schema.table` as required by Trino.

---

## Requirements

### Requirement 1: Natural Language Question Input

**User Story:** As a manufacturing analyst, I want to type a question in plain English, so that I can query production data without knowing SQL or the database schema.

#### Acceptance Criteria

1. THE UI SHALL provide a text input field that accepts natural language questions of up to 2000 characters.
2. WHEN the user submits a question, THE UI SHALL disable the input field and display a loading indicator until the Agent returns a response.
3. WHEN the Agent returns a response, THE UI SHALL re-enable the input field and display the response in the chat history.
4. IF the user submits an empty question, THEN THE UI SHALL display a validation message and SHALL NOT forward the question to the Agent.

---

### Requirement 2: Metadata Retrieval from OpenMetadata

**User Story:** As a manufacturing analyst, I want GlassBot to understand the database structure before generating SQL, so that queries reference real tables and columns rather than guesses.

#### Acceptance Criteria

1. WHEN the Agent receives a user question, THE MetadataService SHALL search OpenMetadata for tables relevant to the question before SQL generation begins.
2. THE MetadataService SHALL retrieve, for each relevant table: the table name, fully qualified name, description, column names, column data types, and available tags or business glossary terms.
3. IF OpenMetadata returns no matching tables for a question, THEN THE Agent SHALL respond to the user with a message stating that no relevant tables were found and SHALL NOT attempt SQL generation.
4. IF the OpenMetadata API is unreachable, THEN THE MetadataService SHALL raise a service error that THE Agent SHALL catch and present to the user as a connectivity error message.
5. THE MetadataService SHALL limit metadata retrieval to the top 5 most relevant tables per question to keep LLM context within token limits.

---

### Requirement 3: SQL Generation

**User Story:** As a manufacturing analyst, I want GlassBot to generate correct Trino SQL from my question, so that I receive accurate data without writing queries manually.

#### Acceptance Criteria

1. WHEN metadata has been successfully retrieved, THE SQLGenerator SHALL use the retrieved metadata and the user's question as context to prompt the LLM to produce a Trino-compatible SQL query.
2. THE SQLGenerator SHALL instruct the LLM to use fully qualified table names in the form `catalog.schema.table` in every generated query.
3. THE SQLGenerator SHALL instruct the LLM to avoid SELECT * unless the user's question explicitly requests all columns.
4. THE SQLGenerator SHALL instruct the LLM to apply appropriate JOINs, aggregates, GROUP BY, ORDER BY, and LIMIT clauses when the question requires them.
5. THE SQLGenerator SHALL include the retrieved column descriptions and table relationships in the LLM prompt to improve join accuracy.
6. THE SQLGenerator SHALL expose a provider-agnostic LLM interface so that the underlying model can be replaced (OpenAI, Azure OpenAI, Anthropic, Ollama) by changing configuration without modifying SQLGenerator logic.

---

### Requirement 4: SQL Validation

**User Story:** As a system administrator, I want GlassBot to validate and display generated SQL before execution, so that only safe, read-only queries run against the database.

#### Acceptance Criteria

1. WHEN the SQLGenerator produces a SQL string, THE SQLValidator SHALL inspect the first meaningful keyword of the query.
2. IF the first meaningful keyword of the query is one of DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE, or CREATE, THEN THE SQLValidator SHALL reject the query, return a validation error, and THE Agent SHALL present the rejection reason to the user without executing the query.
3. WHEN a query passes validation, THE UI SHALL display the generated SQL in an expandable SQL viewer panel before presenting the final results.
4. THE SQLValidator SHALL accept queries whose first meaningful keyword is SELECT, WITH, or EXPLAIN.
5. IF the SQLValidator cannot parse the SQL string to determine the statement type, THEN THE SQLValidator SHALL reject the query with an unparseable-SQL error message.

---

### Requirement 5: Query Execution via Trino

**User Story:** As a manufacturing analyst, I want GlassBot to run the validated SQL against the Trino database, so that I receive real production data in response to my questions.

#### Acceptance Criteria

1. WHEN a query passes SQL validation, THE TrinoClient SHALL execute the query against the configured Trino instance.
2. THE TrinoClient SHALL record the wall-clock execution time from query submission to result receipt.
3. WHEN the query completes successfully, THE TrinoClient SHALL return a QueryResult containing the result rows, the total row count, and the execution time in milliseconds.
4. THE TrinoClient SHALL connect to Trino using the host, port, catalog, and schema values supplied via environment configuration.
5. IF the Trino query returns more than 1000 rows, THEN THE TrinoClient SHALL truncate the result to 1000 rows and SHALL include a truncation notice in the QueryResult.
6. IF Trino returns a query execution error, THEN THE TrinoClient SHALL catch the error and THE Agent SHALL present the error message to the user in plain language without exposing raw stack traces.

---

### Requirement 6: Natural Language Result Summary

**User Story:** As a manufacturing analyst, I want GlassBot to explain the query results in plain English, so that I can understand the data without interpreting raw table output.

#### Acceptance Criteria

1. WHEN a QueryResult is received, THE ResponseFormatter SHALL pass the result rows, row count, execution time, and the original user question to the LLM to generate a natural language summary.
2. THE ResponseFormatter SHALL include the row count and execution time in the summary presented to the user.
3. IF the QueryResult contains zero rows, THEN THE ResponseFormatter SHALL generate a summary stating that no data matched the query conditions rather than displaying an empty table.
4. THE UI SHALL display the natural language summary, the results table, the row count, and the execution time as separate UI elements in the chat response.

---

### Requirement 7: Conversational Memory and Follow-up Questions

**User Story:** As a manufacturing analyst, I want to ask follow-up questions that reference my previous queries, so that I can explore data iteratively without repeating context.

#### Acceptance Criteria

1. THE ConversationMemory SHALL retain the full message history of the current Session, including user questions, generated SQL, and Agent responses.
2. WHEN the user submits a follow-up question, THE Agent SHALL include the recent conversation history from ConversationMemory in the LLM context for SQL generation.
3. THE ConversationMemory SHALL store a minimum of 10 previous conversation turns per Session.
4. WHEN the user clicks the "Clear Conversation" button, THE ConversationMemory SHALL reset the Session history and THE UI SHALL clear the chat display.
5. WHEN a Session ends (browser close or navigation away), THE ConversationMemory SHALL discard the Session history.

---

### Requirement 8: Error Handling

**User Story:** As a manufacturing analyst, I want GlassBot to give me clear error messages when something goes wrong, so that I can understand the problem and rephrase or retry.

#### Acceptance Criteria

1. IF the MetadataService finds no tables matching the user's question, THEN THE Agent SHALL respond with a message indicating that no relevant tables were found and suggesting that the user rephrase the question.
2. IF the SQLGenerator produces a SQL query that THE SQLValidator rejects, THEN THE Agent SHALL respond with the rejection reason and SHALL NOT execute the query.
3. IF THE TrinoClient encounters a query execution error, THEN THE Agent SHALL respond with a plain-language error message that omits internal stack traces.
4. IF the LLM API call fails or times out, THEN THE Agent SHALL respond with a message indicating a temporary service issue and SHALL log the error details.
5. IF the user's question is ambiguous and cannot be mapped to any table with confidence, THEN THE Agent SHALL respond with a clarifying question listing the candidate tables or topics identified.
6. THE Agent SHALL present all error messages in the chat UI in a visually distinct error style.

---

### Requirement 9: Query Result Display

**User Story:** As a manufacturing analyst, I want to see structured query output alongside the SQL and metadata used, so that I can audit and trust the results.

#### Acceptance Criteria

1. THE UI SHALL display query results in a scrollable table showing column headers and row values.
2. THE UI SHALL display the generated SQL in a collapsible code block labeled "Generated SQL".
3. THE UI SHALL display the retrieved metadata summary in a collapsible panel labeled "Metadata Used".
4. THE UI SHALL display the execution time in milliseconds and the row count below the results table.
5. WHERE the QueryResult has been truncated to 1000 rows, THE UI SHALL display a notice stating that the result was truncated.

---

### Requirement 10: Logging

**User Story:** As a system operator, I want GlassBot to log all key events, so that I can monitor system behavior and diagnose failures.

#### Acceptance Criteria

1. THE Agent SHALL log each of the following events for every user question: the user question text, the metadata retrieved, the prompt sent to the LLM, the generated SQL, the SQL validation result, the query execution time, the row count returned, and the LLM response text.
2. IF any component raises an error, THEN THE Agent SHALL log the error type, error message, and the component that raised it at ERROR log level.
3. THE Logger SHALL write log entries to a file and to stdout simultaneously.
4. THE Logger SHALL apply the log level specified by the LOG_LEVEL environment variable; the default log level SHALL be INFO.
5. THE Logger SHALL include a timestamp and the originating component name in every log entry.

---

### Requirement 11: Configuration via Environment Variables

**User Story:** As a system operator, I want all external service credentials and endpoints to be configurable via environment variables, so that GlassBot can be deployed in different environments without code changes.

#### Acceptance Criteria

1. THE GlassBot application SHALL read all external service configuration from environment variables or a `.env` file at startup.
2. THE configuration SHALL include at minimum: OPENAI_API_KEY, TRINO_HOST, TRINO_PORT, TRINO_CATALOG, TRINO_SCHEMA, OPENMETADATA_URL, OPENMETADATA_API_TOKEN, and LOG_LEVEL.
3. IF a required configuration variable is missing at startup, THEN THE GlassBot application SHALL exit with a descriptive error message identifying the missing variable.
4. THE repository SHALL include a `.env.example` file listing all required and optional configuration variables with placeholder values and descriptions.

---

### Requirement 12: LLM Provider Abstraction

**User Story:** As a system operator, I want to swap the LLM provider without changing application logic, so that GlassBot can run on different AI backends depending on cost, availability, or compliance requirements.

#### Acceptance Criteria

1. THE Agent SHALL interact with the LLM exclusively through a provider-agnostic LLM interface.
2. THE LLM interface SHALL support at minimum: OpenAI GPT-4, Azure OpenAI, Anthropic Claude, and Ollama as selectable backends.
3. WHEN the LLM_PROVIDER configuration variable is set to a supported provider name, THE Agent SHALL instantiate the corresponding LLM backend without requiring code changes.
4. IF the LLM_PROVIDER configuration variable is set to an unsupported value, THEN THE GlassBot application SHALL exit with a descriptive error message listing the supported provider names.

---

### Requirement 13: Docker Deployment

**User Story:** As a system operator, I want to run GlassBot in a Docker container, so that setup is reproducible and environment-independent.

#### Acceptance Criteria

1. THE repository SHALL include a Dockerfile that builds a GlassBot image using Python 3.12 as the base.
2. THE repository SHALL include a Docker Compose file that defines services for GlassBot, and that accepts Trino and OpenMetadata connection parameters via environment variables.
3. WHEN the Docker Compose stack is started, THE GlassBot service SHALL expose the Streamlit UI on port 8501.
4. THE Dockerfile SHALL install all dependencies listed in `requirements.txt` using pinned version numbers.

---

### Requirement 14: Unit Tests

**User Story:** As a developer, I want unit tests for key modules, so that I can verify correctness and prevent regressions.

#### Acceptance Criteria

1. THE test suite SHALL include unit tests for the SQLValidator covering: acceptance of SELECT queries, acceptance of WITH (CTE) queries, acceptance of EXPLAIN queries, rejection of DELETE queries, rejection of UPDATE queries, rejection of INSERT queries, rejection of DROP queries, rejection of ALTER queries, rejection of TRUNCATE queries, and rejection of CREATE queries.
2. THE test suite SHALL include unit tests for the MetadataService covering: successful table search returning structured metadata, handling of empty search results, and handling of API connectivity errors.
3. THE test suite SHALL include unit tests for the ResponseFormatter covering: formatting of non-empty result sets, formatting of empty result sets, and inclusion of row count and execution time in the summary.
4. THE test suite SHALL include a round-trip property test for SQL generation: FOR ALL valid natural language questions that produce a SQL query, parsing the generated SQL to extract the statement type SHALL return a Safe Statement type.
5. THE test suite SHALL be executable with a single command using pytest.
