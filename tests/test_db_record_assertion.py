"""Tests for DB record assertion scenario (TC-02 from Section 5).

Scenario: DB record assertion (TC-02 from Section 5)
Given a running system with database accessible to harness
And a scenario with env: { "order_id": "ord_123" }
And assertions: [ { "type": "db_record", "table": "orders", "conditions": { "id": "ord_123", "status": "pending" } } ]
When the harness executes the scenario
Then the harness queries the orders table for id=ord_123
And asserts the record exists with status=pending
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestDBRecordAssertionScenario:
    """Tests for DB record assertion scenario (TC-02 from Section 5)."""

    @pytest.fixture
    def db_record_scenario_yaml(self) -> str:
        """Sample scenario with db_record assertion matching SPEC.md."""
        return """name: order-pending-check
env:
  order_id: ord_123
trigger:
  type: http
  method: POST
  path: /api/orders
  body:
    items:
      - sku-a
assertions:
  - type: db_record
    table: orders
    conditions:
      id: ord_123
      status: pending
"""

    @pytest.fixture
    def db_record_scenario_dict(self, db_record_scenario_yaml) -> dict:
        """Sample scenario as dict."""
        return yaml.safe_load(db_record_scenario_yaml)

    def test_db_record_scenario_parses_correctly(self, db_record_scenario_dict):
        """Scenario parses correctly with env and db_record assertion."""
        assert db_record_scenario_dict["name"] == "order-pending-check"
        assert db_record_scenario_dict["env"]["order_id"] == "ord_123"

    def test_db_record_assertion_has_correct_format(self, db_record_scenario_dict):
        """db_record assertion has correct format: table + conditions (not query)."""
        assertion = db_record_scenario_dict["assertions"][0]
        assert assertion["type"] == "db_record"
        assert assertion["table"] == "orders"
        assert assertion["conditions"]["id"] == "ord_123"
        assert assertion["conditions"]["status"] == "pending"
        # Should NOT have 'query' field - uses table + conditions instead
        assert "query" not in assertion

    def test_db_record_assertion_supports_multiple_conditions(self, db_record_scenario_dict):
        """db_record assertion conditions can have multiple fields."""
        # Extended scenario with multiple conditions
        scenario = {
            'name': 'multi-condition-check',
            'env': {'order_id': 'ord_123'},
            'assertions': [
                {
                    'type': 'db_record',
                    'table': 'orders',
                    'conditions': {
                        'id': 'ord_123',
                        'status': 'pending',
                        'customer_id': 'cust_456'
                    }
                }
            ]
        }
        assertion = scenario["assertions"][0]
        assert assertion["conditions"]["id"] == "ord_123"
        assert assertion["conditions"]["status"] == "pending"
        assert assertion["conditions"]["customer_id"] == "cust_456"


class TestHarnessDBRecordAssertion:
    """Tests for harness db_record assertion execution."""

    def test_harness_has_check_db_record_function(self):
        """Harness has check_db_record function for db_record assertions."""
        from harness.scenario_harness import check_db_record
        assert callable(check_db_record)

    def test_check_db_record_with_table_and_conditions(self):
        """check_db_record accepts table and conditions (not just query)."""
        from harness.scenario_harness import check_db_record

        # Mock the database query execution
        with patch('harness.scenario_harness.assert_db_record') as mock_assert:
            mock_assert.return_value = True
            
            # The function should support table + conditions format
            result = check_db_record(
                table="orders",
                conditions={"id": "ord_123", "status": "pending"}
            )
            
            # Verify the mock was called with appropriate query
            mock_assert.assert_called_once()
            call_args = mock_assert.call_args
            # Check that a query was generated from table + conditions
            query = call_args[0][0]
            assert "orders" in query.lower()
            assert "ord_123" in query
            assert "pending" in query


class TestDBRecordBuildsQueryFromConditions:
    """Tests that db_record assertions build correct SQL queries."""

    def test_builds_select_query_from_table_and_conditions(self):
        """Query is built as SELECT * FROM table WHERE conditions."""
        from harness.scenario_harness import check_db_record

        with patch('harness.db.execute_query') as mock_query:
            mock_query.return_value = {"success": True, "row_count": 1}
            
            result = check_db_record(
                table="orders",
                conditions={"id": "ord_123", "status": "pending"}
            )
            
            # Verify query was executed
            mock_query.assert_called_once()
            query = mock_query.call_args[0][0]
            
            # Query should be a SELECT statement
            assert "SELECT" in query.upper()
            assert "FROM" in query.upper()
            assert "orders" in query.lower()
            assert "id" in query.lower()
            assert "ord_123" in query
            assert "status" in query.lower()
            assert "pending" in query.lower()

    def test_query_includes_where_clause(self):
        """Query includes WHERE clause with condition comparisons."""
        from harness.scenario_harness import check_db_record

        with patch('harness.db.execute_query') as mock_query:
            mock_query.return_value = {"success": True, "row_count": 1}
            
            check_db_record(
                table="orders",
                conditions={"id": "ord_123"}
            )
            
            query = mock_query.call_args[0][0]
            assert "WHERE" in query.upper()

    def test_query_handles_string_values_with_quotes(self):
        """String values in conditions are properly quoted in SQL."""
        from harness.scenario_harness import check_db_record

        with patch('harness.db.execute_query') as mock_query:
            mock_query.return_value = {"success": True, "row_count": 1}
            
            check_db_record(
                table="orders",
                conditions={"id": "ord_123"}
            )
            
            query = mock_query.call_args[0][0]
            # String values should be quoted
            assert "'ord_123'" in query or '"ord_123"' in query


class TestDBRecordAssertionExecution:
    """Tests for executing db_record assertions."""

    def test_db_record_assertion_passes_when_record_exists(self):
        """db_record assertion passes when matching record exists."""
        from harness.scenario_harness import check_db_record

        with patch('harness.db.execute_query') as mock_query:
            mock_query.return_value = {"success": True, "row_count": 1}
            
            result = check_db_record(
                table="orders",
                conditions={"id": "ord_123", "status": "pending"}
            )
            
            assert result is True

    def test_db_record_assertion_fails_when_no_record(self):
        """db_record assertion fails when no matching record exists."""
        from harness.scenario_harness import check_db_record

        with patch('harness.scenario_harness.execute_query') as mock_query:
            mock_query.return_value = {"success": True, "row_count": 0}
            
            result = check_db_record(
                table="orders",
                conditions={"id": "ord_999"}
            )
            
            assert result is False

    def test_db_record_assertion_fails_on_query_error(self):
        """db_record assertion fails when query execution fails."""
        from harness.scenario_harness import check_db_record

        with patch('harness.scenario_harness.execute_query') as mock_query:
            mock_query.return_value = {"success": False, "error": "Table not found"}
            
            result = check_db_record(
                table="nonexistent",
                conditions={"id": "ord_123"}
            )
            
            assert result is False


class TestHarnessRunAssertionDBRecord:
    """Tests for harness run_assertion with db_record type."""

    def test_run_assertion_handles_db_record_with_table_and_conditions(self):
        """run_assertion handles db_record assertion with table + conditions format."""
        from harness.scenario_harness import run_assertion

        assertion = {
            'type': 'db_record',
            'table': 'orders',
            'conditions': {'id': 'ord_123', 'status': 'pending'}
        }

        with patch('harness.db.execute_query') as mock_query:
            mock_query.return_value = {"success": True, "row_count": 1}
            
            result = run_assertion(assertion, "http://localhost:8080")
            
            assert result is True

    def test_run_assertion_db_record_returns_false_when_no_match(self):
        """run_assertion returns False for db_record when no matching record."""
        from harness.scenario_harness import run_assertion

        assertion = {
            'type': 'db_record',
            'table': 'orders',
            'conditions': {'id': 'ord_999', 'status': 'pending'}
        }

        with patch('harness.scenario_harness.execute_query') as mock_query:
            mock_query.return_value = {"success": True, "row_count": 0}
            
            result = run_assertion(assertion, "http://localhost:8080")
            
            assert result is False


class TestDBRecordScenarioExecution:
    """Integration tests for full DB record scenario execution."""

    def test_full_db_record_scenario_flow(self, temp_scenarios_dir, temp_signal_path):
        """Full flow: execute trigger, check db_record assertion, write signal."""
        from harness.scenario_harness import run_scenario, write_result

        scenario = {
            'name': 'order-pending-check',
            'env': {'order_id': 'ord_123'},
            'trigger': {
                'type': 'http',
                'method': 'POST',
                'path': '/api/orders',
                'body': {'items': ['sku-a']}
            },
            'assertions': [
                {
                    'type': 'db_record',
                    'table': 'orders',
                    'conditions': {'id': 'ord_123', 'status': 'pending'}
                }
            ]
        }

        # Mock HTTP trigger response
        mock_http_response = MagicMock()
        mock_http_response.status = 201
        mock_http_response.__enter__ = MagicMock(return_value=mock_http_response)
        mock_http_response.__exit__ = MagicMock(return_value=False)

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', return_value=mock_http_response):
                with patch('harness.db.execute_query') as mock_query:
                    mock_query.return_value = {"success": True, "row_count": 1}
                    
                    # Run the scenario
                    passed = run_scenario(scenario, "http://localhost:8080")
                    
                    # Write signal
                    write_result(passed)
                    
                    # Verify signal
                    assert passed is True
                    assert temp_signal_path.exists()
                    with open(temp_signal_path) as f:
                        signal = json.load(f)
                    assert signal == {"pass": True}

    def test_db_record_scenario_fails_when_status_not_pending(self, temp_scenarios_dir, temp_signal_path):
        """Scenario fails when db_record assertion finds wrong status."""
        from harness.scenario_harness import run_scenario, write_result

        scenario = {
            'name': 'order-pending-check',
            'env': {'order_id': 'ord_123'},
            'trigger': {
                'type': 'http',
                'method': 'POST',
                'path': '/api/orders',
                'body': {'items': ['sku-a']}
            },
            'assertions': [
                {
                    'type': 'db_record',
                    'table': 'orders',
                    'conditions': {'id': 'ord_123', 'status': 'pending'}
                }
            ]
        }

        mock_http_response = MagicMock()
        mock_http_response.status = 200
        mock_http_response.__enter__ = MagicMock(return_value=mock_http_response)
        mock_http_response.__exit__ = MagicMock(return_value=False)

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', return_value=mock_http_response):
                with patch('harness.scenario_harness.execute_query') as mock_query:
                    # Return no matching record (status is not 'pending')
                    mock_query.return_value = {"success": True, "row_count": 0}
                    
                    passed = run_scenario(scenario, "http://localhost:8080")
                    write_result(passed)
                    
                    assert passed is False
                    with open(temp_signal_path) as f:
                        signal = json.load(f)
                    assert signal == {"pass": False}


class TestHarnessClassDBRecord:
    """Tests for Harness class db_record assertion support."""

    def test_harness_class_has_check_db_record_method(self):
        """Harness class has check_db_record method."""
        from harness.scenario_harness import Harness

        harness = Harness(base_url="http://localhost:8080")
        assert hasattr(harness, 'check_db_record') or hasattr(harness, 'execute_db_record')

    def test_harness_can_check_db_record(self):
        """Harness can execute db_record assertions."""
        from harness.scenario_harness import Harness

        harness = Harness(base_url="http://localhost:8080")

        with patch('harness.db.execute_query') as mock_query:
            mock_query.return_value = {"success": True, "row_count": 1}
            
            # Try calling check_db_record or similar method
            if hasattr(harness, 'check_db_record'):
                result = harness.check_db_record(
                    table="orders",
                    conditions={"id": "ord_123"}
                )
                assert result is True
            elif hasattr(harness, 'execute_db_record'):
                result = harness.execute_db_record(
                    table="orders",
                    conditions={"id": "ord_123"}
                )
                assert result is True


class TestEnvVariableSupport:
    """Tests for environment variable support in scenarios."""

    def test_scenario_can_have_env_variables(self):
        """Scenario supports env field with variables."""
        scenario = {
            'name': 'test',
            'env': {'order_id': 'ord_123'},
            'assertions': []
        }
        
        assert scenario["env"]["order_id"] == "ord_123"

    def test_env_variables_are_accessible(self):
        """Env variables from scenario are accessible."""
        scenario = {
            'name': 'test',
            'env': {'order_id': 'ord_123'},
            'assertions': [
                {
                    'type': 'db_record',
                    'table': 'orders',
                    'conditions': {'id': 'ord_123'}
                }
            ]
        }
        
        env = scenario.get("env", {})
        order_id = env.get("order_id")
        
        assert order_id == "ord_123"
        # Use env in conditions
        conditions = scenario["assertions"][0]["conditions"]
        assert conditions["id"] == order_id
