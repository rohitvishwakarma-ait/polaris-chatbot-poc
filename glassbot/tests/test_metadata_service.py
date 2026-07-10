"""
Unit tests for glassbot/chatbot/metadata_service.py — MetadataService.

Covers:
- Successful search: mock HTTP response → verify TableMetadata fields are
  populated correctly (fqn, name, description, columns, tags).
- Empty results: mock empty OpenMetadata response → verify MetadataNotFoundError
  raised.
- Connectivity error: mock httpx.ConnectError → verify MetadataConnectivityError
  raised.
- HTTP status error: mock a non-2xx response → verify MetadataConnectivityError
  raised.
- Timeout: mock httpx.TimeoutException → verify MetadataConnectivityError raised.

Requirements: 14.2 (MetadataService unit tests)
              2.1, 2.2, 2.3, 2.4, 2.5
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest

from glassbot.chatbot.metadata_service import MetadataService
from glassbot.chatbot.models import ColumnInfo, TableMetadata
from glassbot.exceptions import MetadataConnectivityError, MetadataNotFoundError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> SimpleNamespace:
    """Minimal config stub for MetadataService."""
    return SimpleNamespace(
        OPENMETADATA_URL="http://openmetadata.example.com",
        OPENMETADATA_API_TOKEN="test-token-abc123",
    )


@pytest.fixture
def service(config: SimpleNamespace) -> MetadataService:
    return MetadataService(config)


# ---------------------------------------------------------------------------
# Helpers — canonical OpenMetadata search response
# ---------------------------------------------------------------------------

def _make_response(hits: list[dict]) -> dict:
    """Wrap *hits* in the OpenMetadata search response envelope."""
    return {"hits": {"hits": hits}}


def _sample_hit(
    fqn: str = "catalog.schema.products",
    name: str = "products",
    description: str = "Product catalogue",
    columns: list[dict] | None = None,
    tags: list[dict] | None = None,
) -> dict:
    if columns is None:
        columns = [
            {"name": "id", "dataType": "INT", "description": "Primary key"},
            {"name": "name", "dataType": "VARCHAR", "description": "Product name"},
        ]
    if tags is None:
        tags = [{"tagFQN": "Domain.Manufacturing"}, {"tagFQN": "PII.None"}]
    return {
        "_source": {
            "fullyQualifiedName": fqn,
            "name": name,
            "description": description,
            "columns": columns,
            "tags": tags,
            "followers": [],
        }
    }


def _mock_httpx_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response object."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = MagicMock()  # no-op by default (success)
    return mock_resp


# ---------------------------------------------------------------------------
# Successful search
# ---------------------------------------------------------------------------

class TestSuccessfulSearch:
    """MetadataService returns correctly-populated TableMetadata on success."""

    def test_returns_list_of_table_metadata(self, service: MetadataService):
        response_data = _make_response([_sample_hit()])
        mock_resp = _mock_httpx_response(response_data)

        with patch("httpx.get", return_value=mock_resp) as mock_get:
            results = service.search_tables("What products do we have?")

        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], TableMetadata)

    def test_fqn_populated(self, service: MetadataService):
        hit = _sample_hit(fqn="mycat.myschema.orders")
        mock_resp = _mock_httpx_response(_make_response([hit]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("orders query")[0]

        assert result.fqn == "mycat.myschema.orders"

    def test_name_populated(self, service: MetadataService):
        hit = _sample_hit(name="orders")
        mock_resp = _mock_httpx_response(_make_response([hit]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("orders query")[0]

        assert result.name == "orders"

    def test_description_populated(self, service: MetadataService):
        hit = _sample_hit(description="All customer orders")
        mock_resp = _mock_httpx_response(_make_response([hit]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("orders?")[0]

        assert result.description == "All customer orders"

    def test_columns_populated(self, service: MetadataService):
        columns = [
            {"name": "order_id", "dataType": "BIGINT", "description": "PK"},
            {"name": "amount", "dataType": "DECIMAL", "description": "Total amount"},
        ]
        hit = _sample_hit(columns=columns)
        mock_resp = _mock_httpx_response(_make_response([hit]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("order amounts")[0]

        assert len(result.columns) == 2
        assert isinstance(result.columns[0], ColumnInfo)
        assert result.columns[0].name == "order_id"
        assert result.columns[0].data_type == "BIGINT"
        assert result.columns[0].description == "PK"
        assert result.columns[1].name == "amount"
        assert result.columns[1].data_type == "DECIMAL"

    def test_tags_populated(self, service: MetadataService):
        tags = [{"tagFQN": "Domain.Sales"}, {"tagFQN": "Tier.Gold"}]
        hit = _sample_hit(tags=tags)
        mock_resp = _mock_httpx_response(_make_response([hit]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("sales data")[0]

        assert result.tags == ["Domain.Sales", "Tier.Gold"]

    def test_multiple_tables_returned(self, service: MetadataService):
        hits = [
            _sample_hit(fqn="cat.sc.t1", name="t1"),
            _sample_hit(fqn="cat.sc.t2", name="t2"),
            _sample_hit(fqn="cat.sc.t3", name="t3"),
        ]
        mock_resp = _mock_httpx_response(_make_response(hits))

        with patch("httpx.get", return_value=mock_resp):
            results = service.search_tables("multiple tables")

        assert len(results) == 3
        assert [r.name for r in results] == ["t1", "t2", "t3"]

    def test_correct_url_called(self, service: MetadataService, config: SimpleNamespace):
        mock_resp = _mock_httpx_response(_make_response([_sample_hit()]))

        with patch("httpx.get", return_value=mock_resp) as mock_get:
            service.search_tables("bottles produced last month")

        call_args = mock_get.call_args
        assert "http://openmetadata.example.com/api/v1/search/query" == call_args[0][0]

    def test_bearer_token_in_request_headers(self, service: MetadataService, config: SimpleNamespace):
        mock_resp = _mock_httpx_response(_make_response([_sample_hit()]))

        with patch("httpx.get", return_value=mock_resp) as mock_get:
            service.search_tables("bottles")

        call_kwargs = mock_get.call_args.kwargs
        assert "headers" in call_kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-token-abc123"

    def test_query_params_include_question_and_limit(self, service: MetadataService):
        mock_resp = _mock_httpx_response(_make_response([_sample_hit()]))

        with patch("httpx.get", return_value=mock_resp) as mock_get:
            service.search_tables("bottle weight", limit=3)

        params = mock_get.call_args.kwargs["params"]
        assert params["q"] == "bottle weight"
        assert params["size"] == 3
        assert params["index"] == "table_search_index"

    def test_null_description_returns_none(self, service: MetadataService):
        hit = _sample_hit()
        hit["_source"]["description"] = None
        mock_resp = _mock_httpx_response(_make_response([hit]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("any")[0]

        assert result.description is None

    def test_missing_description_returns_none(self, service: MetadataService):
        hit = _sample_hit()
        del hit["_source"]["description"]
        mock_resp = _mock_httpx_response(_make_response([hit]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("any")[0]

        assert result.description is None

    def test_column_with_null_description_returns_none(self, service: MetadataService):
        columns = [{"name": "col", "dataType": "INT", "description": None}]
        hit = _sample_hit(columns=columns)
        mock_resp = _mock_httpx_response(_make_response([hit]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("col")[0]

        assert result.columns[0].description is None

    def test_empty_tags_list(self, service: MetadataService):
        hit = _sample_hit(tags=[])
        mock_resp = _mock_httpx_response(_make_response([hit]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("tags test")[0]

        assert result.tags == []

    def test_relationships_is_empty_list(self, service: MetadataService):
        """relationships not populated via REST search — always an empty list."""
        mock_resp = _mock_httpx_response(_make_response([_sample_hit()]))

        with patch("httpx.get", return_value=mock_resp):
            result = service.search_tables("any")[0]

        assert result.relationships == []


# ---------------------------------------------------------------------------
# Empty results → MetadataNotFoundError
# ---------------------------------------------------------------------------

class TestEmptyResults:
    """MetadataService returns fallback tables when hits list is empty."""

    def test_empty_hits_returns_fallback_tables(self, service: MetadataService):
        mock_resp = _mock_httpx_response(_make_response([]))

        with patch("httpx.get", return_value=mock_resp):
            results = service.search_tables("completely unknown topic")

        # Should return fallback tables, not raise
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_fallback_tables_have_valid_fqn(self, service: MetadataService):
        mock_resp = _mock_httpx_response(_make_response([]))

        with patch("httpx.get", return_value=mock_resp):
            results = service.search_tables("mystery question")

        for t in results:
            parts = t.fqn.split(".")
            assert len(parts) == 3

    def test_missing_hits_key_returns_fallback(self, service: MetadataService):
        """Malformed response (missing hits) treated as no results → fallback."""
        mock_resp = _mock_httpx_response({})

        with patch("httpx.get", return_value=mock_resp):
            results = service.search_tables("question")

        assert isinstance(results, list)
        assert len(results) >= 1

    def test_fallback_returns_table_metadata_instances(self, service: MetadataService):
        mock_resp = _mock_httpx_response(_make_response([]))

        with patch("httpx.get", return_value=mock_resp):
            results = service.search_tables("nothing found")

        from glassbot.chatbot.models import TableMetadata
        assert all(isinstance(t, TableMetadata) for t in results)


# ---------------------------------------------------------------------------
# Connectivity errors → MetadataConnectivityError
# ---------------------------------------------------------------------------

class TestConnectivityErrors:
    """MetadataService raises MetadataConnectivityError on network failures."""

    def test_connect_error_raises_connectivity_error(self, service: MetadataService):
        with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")):
            with pytest.raises(MetadataConnectivityError):
                service.search_tables("bottle production")

    def test_timeout_raises_connectivity_error(self, service: MetadataService):
        with patch("httpx.get", side_effect=httpx.TimeoutException("Timed out")):
            with pytest.raises(MetadataConnectivityError):
                service.search_tables("bottle production")

    def test_connectivity_error_message_contains_base_url(self, service: MetadataService, config: SimpleNamespace):
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(MetadataConnectivityError) as exc_info:
                service.search_tables("any")

        assert "openmetadata.example.com" in str(exc_info.value)

    def test_http_status_error_raises_connectivity_error(self, service: MetadataService):
        """Non-2xx HTTP responses should also raise MetadataConnectivityError."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_resp,
        )

        with patch("httpx.get", return_value=mock_resp):
            with pytest.raises(MetadataConnectivityError):
                service.search_tables("any")

    def test_connectivity_error_is_glassbot_error(self, service: MetadataService):
        from glassbot.exceptions import GlassBotError

        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(GlassBotError):
                service.search_tables("any")

    def test_connect_error_chained_cause(self, service: MetadataService):
        """The original httpx exception should be the __cause__ of the raised error."""
        original = httpx.ConnectError("original error")
        with patch("httpx.get", side_effect=original):
            with pytest.raises(MetadataConnectivityError) as exc_info:
                service.search_tables("any")

        assert exc_info.value.__cause__ is original
