"""
Unit tests for glassbot/utils/validators.py — SQLValidator.

Covers:
- Acceptance of SELECT, WITH (CTE), EXPLAIN (case-insensitive, leading
  whitespace, inline comments)
- Rejection of DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE, CREATE
- Rejection of empty string and non-SQL text

Requirements: 14.1
"""

from __future__ import annotations

import pytest

from utils.validators import ALLOWLIST, BLOCKLIST, SQLValidator
from chatbot.models import ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def validator() -> SQLValidator:
    return SQLValidator()


# ---------------------------------------------------------------------------
# ALLOWLIST — statements that must be accepted
# ---------------------------------------------------------------------------

class TestAllowlistStatements:
    """SQLValidator must accept SELECT, WITH, and EXPLAIN queries."""

    # SELECT ------------------------------------------------------------------

    def test_select_simple(self, validator: SQLValidator):
        r = validator.validate("SELECT 1")
        assert r.is_valid is True
        assert r.statement_type == "SELECT"
        assert r.error_message is None

    def test_select_from_table(self, validator: SQLValidator):
        r = validator.validate("SELECT * FROM catalog.schema.table")
        assert r.is_valid is True
        assert r.statement_type == "SELECT"

    def test_select_lowercase(self, validator: SQLValidator):
        r = validator.validate("select id, name from products limit 10")
        assert r.is_valid is True
        assert r.statement_type == "SELECT"

    def test_select_mixed_case(self, validator: SQLValidator):
        r = validator.validate("Select id From foo")
        assert r.is_valid is True
        assert r.statement_type == "SELECT"

    def test_select_leading_whitespace(self, validator: SQLValidator):
        r = validator.validate("   SELECT 1")
        assert r.is_valid is True
        assert r.statement_type == "SELECT"

    def test_select_leading_newlines(self, validator: SQLValidator):
        r = validator.validate("\n\n\tSELECT 1")
        assert r.is_valid is True
        assert r.statement_type == "SELECT"

    def test_select_after_single_line_comment(self, validator: SQLValidator):
        r = validator.validate("-- find all items\nSELECT * FROM items")
        assert r.is_valid is True
        assert r.statement_type == "SELECT"

    def test_select_after_block_comment(self, validator: SQLValidator):
        r = validator.validate("/* analytics query */\nSELECT count(*) FROM orders")
        assert r.is_valid is True
        assert r.statement_type == "SELECT"

    # WITH / CTE --------------------------------------------------------------

    def test_with_cte(self, validator: SQLValidator):
        sql = "WITH cte AS (SELECT 1) SELECT * FROM cte"
        r = validator.validate(sql)
        assert r.is_valid is True
        assert r.statement_type == "WITH"
        assert r.error_message is None

    def test_with_lowercase(self, validator: SQLValidator):
        sql = "with cte as (select 1) select * from cte"
        r = validator.validate(sql)
        assert r.is_valid is True
        assert r.statement_type == "WITH"

    def test_with_leading_whitespace(self, validator: SQLValidator):
        sql = "  WITH cte AS (SELECT count(*) FROM foo) SELECT * FROM cte"
        r = validator.validate(sql)
        assert r.is_valid is True
        assert r.statement_type == "WITH"

    # EXPLAIN -----------------------------------------------------------------

    def test_explain_select(self, validator: SQLValidator):
        r = validator.validate("EXPLAIN SELECT * FROM orders")
        assert r.is_valid is True
        assert r.statement_type == "EXPLAIN"
        assert r.error_message is None

    def test_explain_lowercase(self, validator: SQLValidator):
        r = validator.validate("explain select * from orders")
        assert r.is_valid is True
        assert r.statement_type == "EXPLAIN"

    def test_explain_leading_whitespace(self, validator: SQLValidator):
        r = validator.validate("   EXPLAIN SELECT 1")
        assert r.is_valid is True
        assert r.statement_type == "EXPLAIN"


# ---------------------------------------------------------------------------
# BLOCKLIST — destructive statements that must be rejected
# ---------------------------------------------------------------------------

class TestBlocklistStatements:
    """SQLValidator must reject all destructive SQL statement types."""

    def test_delete(self, validator: SQLValidator):
        r = validator.validate("DELETE FROM customers WHERE id = 1")
        assert r.is_valid is False
        assert r.statement_type == "DELETE"
        assert r.error_message is not None
        assert "DELETE" in r.error_message

    def test_update(self, validator: SQLValidator):
        r = validator.validate("UPDATE products SET price = 10 WHERE id = 5")
        assert r.is_valid is False
        assert r.statement_type == "UPDATE"
        assert r.error_message is not None
        assert "UPDATE" in r.error_message

    def test_insert(self, validator: SQLValidator):
        r = validator.validate("INSERT INTO logs (msg) VALUES ('hello')")
        assert r.is_valid is False
        assert r.statement_type == "INSERT"
        assert r.error_message is not None
        assert "INSERT" in r.error_message

    def test_drop(self, validator: SQLValidator):
        r = validator.validate("DROP TABLE sensitive_data")
        assert r.is_valid is False
        assert r.statement_type == "DROP"
        assert r.error_message is not None
        assert "DROP" in r.error_message

    def test_alter(self, validator: SQLValidator):
        r = validator.validate("ALTER TABLE products ADD COLUMN weight DECIMAL(10,2)")
        assert r.is_valid is False
        assert r.statement_type == "ALTER"
        assert r.error_message is not None
        assert "ALTER" in r.error_message

    def test_truncate(self, validator: SQLValidator):
        r = validator.validate("TRUNCATE TABLE audit_log")
        assert r.is_valid is False
        assert r.statement_type == "TRUNCATE"
        assert r.error_message is not None
        assert "TRUNCATE" in r.error_message

    def test_create(self, validator: SQLValidator):
        r = validator.validate("CREATE TABLE new_table (id INT, name VARCHAR(100))")
        assert r.is_valid is False
        assert r.statement_type == "CREATE"
        assert r.error_message is not None
        assert "CREATE" in r.error_message

    def test_delete_lowercase(self, validator: SQLValidator):
        r = validator.validate("delete from orders")
        assert r.is_valid is False
        assert r.statement_type == "DELETE"

    def test_drop_leading_whitespace(self, validator: SQLValidator):
        r = validator.validate("  DROP VIEW my_view")
        assert r.is_valid is False
        assert r.statement_type == "DROP"

    def test_blocklist_error_message_format(self, validator: SQLValidator):
        """The error message should contain the keyword and describe it as not allowed."""
        r = validator.validate("DELETE FROM foo")
        assert "DELETE" in r.error_message
        assert "not allowed" in r.error_message.lower()


# ---------------------------------------------------------------------------
# UNPARSEABLE — inputs that should be rejected with "unparseable-SQL"
# ---------------------------------------------------------------------------

class TestUnparseableStatements:
    """SQLValidator must reject inputs where statement type cannot be determined."""

    def test_empty_string(self, validator: SQLValidator):
        r = validator.validate("")
        assert r.is_valid is False
        assert r.statement_type is None
        assert r.error_message == "unparseable-SQL"

    def test_whitespace_only(self, validator: SQLValidator):
        r = validator.validate("   \n\t  ")
        assert r.is_valid is False
        assert r.statement_type is None
        assert r.error_message == "unparseable-SQL"

    def test_non_sql_text(self, validator: SQLValidator):
        r = validator.validate("this is not sql at all")
        assert r.is_valid is False
        assert r.statement_type is None
        assert r.error_message == "unparseable-SQL"

    def test_just_a_number(self, validator: SQLValidator):
        r = validator.validate("12345")
        assert r.is_valid is False
        assert r.statement_type is None
        assert r.error_message == "unparseable-SQL"

    def test_only_comment(self, validator: SQLValidator):
        r = validator.validate("-- just a comment, no statement")
        assert r.is_valid is False
        assert r.statement_type is None
        assert r.error_message == "unparseable-SQL"


# ---------------------------------------------------------------------------
# Return type verification
# ---------------------------------------------------------------------------

class TestReturnType:
    """Ensure validate() always returns a ValidationResult instance."""

    def test_returns_validation_result_for_valid(self, validator: SQLValidator):
        r = validator.validate("SELECT 1")
        assert isinstance(r, ValidationResult)

    def test_returns_validation_result_for_invalid(self, validator: SQLValidator):
        r = validator.validate("DELETE FROM foo")
        assert isinstance(r, ValidationResult)

    def test_returns_validation_result_for_unparseable(self, validator: SQLValidator):
        r = validator.validate("")
        assert isinstance(r, ValidationResult)

    def test_valid_result_has_no_error_message(self, validator: SQLValidator):
        r = validator.validate("SELECT 1")
        assert r.error_message is None

    def test_invalid_result_has_error_message(self, validator: SQLValidator):
        r = validator.validate("DROP TABLE foo")
        assert r.error_message is not None
        assert len(r.error_message) > 0
