# GlassBot

GlassBot is an AI-powered chatbot for glass bottle manufacturing. It lets operators and analysts query production data in plain English — GlassBot translates natural-language questions into SQL, runs them against a Trino data warehouse, and presents clear, formatted answers in a Streamlit web UI.

---

## Prerequisites

- **Python 3.12+** (for local development)
- **Docker & Docker Compose** (for containerised deployment)
- A running **Trino** instance with the glass bottle manufacturing catalog
- A running **OpenMetadata** instance (provides table/column metadata for SQL generation)

---

## Setup

1. Copy the environment variable template and fill in your credentials:

   ```bash
   cp .env.example .env
   ```

2. Open `.env` and set the required values (see the [Environment Variables](#environment-variables) table below).

---

## Running with Docker Compose

```bash
docker compose up --build
```

The app will be available at <http://localhost:8501>.

To run in the background:

```bash
docker compose up --build -d
```

To stop:

```bash
docker compose down
```

---

## Running Locally

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the app
streamlit run app.py
```

The app will be available at <http://localhost:8501>.

---

## Running the Test Suite

**Unit and property-based tests** (no live services required):

```bash
pytest tests/
```

**Integration tests** (require a live Trino and OpenMetadata instance):

```bash
pytest tests/integration/ -m integration
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | ✅ | — | Provider and model string, e.g. `openai:gpt-4o` or `anthropic:claude-3-5-sonnet-20241022` |
| `OPENAI_API_KEY` | ✅ when using OpenAI | — | API key from [platform.openai.com](https://platform.openai.com/api-keys) |
| `AZURE_OPENAI_ENDPOINT` | ✅ when using Azure OpenAI | — | Full Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | ✅ when using Azure OpenAI | — | Azure OpenAI API key |
| `ANTHROPIC_API_KEY` | ✅ when using Anthropic | — | API key from [console.anthropic.com](https://console.anthropic.com/) |
| `OLLAMA_BASE_URL` | ✅ when using Ollama | `http://localhost:11434` | Base URL of the local Ollama instance |
| `TRINO_HOST` | ✅ | `localhost` | Hostname or IP of the Trino coordinator |
| `TRINO_PORT` | ✅ | `8080` | Trino coordinator HTTP port |
| `TRINO_CATALOG` | ✅ | `glass_bottle` | Trino catalog containing manufacturing data |
| `TRINO_SCHEMA` | ✅ | `manufacturing` | Default Trino schema within the catalog |
| `TRINO_USER` | ✅ | `glassbot` | Trino username |
| `OPENMETADATA_URL` | ✅ | — | Base URL of the OpenMetadata server, e.g. `http://localhost:8585` |
| `OPENMETADATA_API_TOKEN` | ✅ | — | OpenMetadata personal access token |
| `LOG_LEVEL` | ☑️ optional | `INFO` | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FILE` | ☑️ optional | `glassbot.log` | Path to the application log file |
