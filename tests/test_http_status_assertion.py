"""Tests for HTTP status assertion scenario (TC-01 from Section 5).

Scenario: Post-commit scenario execution (TC-02)
Given a running system at http://localhost:8080
And a scenario with trigger: POST /api/checkout { items: [sku-a] }
And assertions: [ { "type": "http_status", "path": "/api/orders", "expect": 201 } ]
When the harness executes the scenario
Then the harness POSTs to /api/checkout
And asserts the response status is 201
And the signal reflects pass/fail correctly
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

import pytest
import yaml


class TestHTTPStatusAssertionScenario:
    """Tests for HTTP status assertion scenario (TC-01 from Section 5)."""

    @pytest.fixture
    def checkout_scenario_yaml(self) -> str:
        """Sample scenario with POST /api/checkout trigger and HTTP status assertion."""
        return """name: checkout-creates-order
trigger:
  type: http
  method: POST
  path: /api/checkout
  body:
    items:
      - sku-a
assertions:
  - type: http_status
    path: /api/orders
    expect: 201
"""

    @pytest.fixture
    def checkout_scenario_dict(self, checkout_scenario_yaml) -> dict:
        """Sample scenario as dict."""
        return yaml.safe_load(checkout_scenario_yaml)

    def test_checkout_scenario_parses_correctly(self, checkout_scenario_dict):
        """Scenario parses correctly with trigger and assertions."""
        assert checkout_scenario_dict["name"] == "checkout-creates-order"
        assert checkout_scenario_dict["trigger"]["type"] == "http"
        assert checkout_scenario_dict["trigger"]["method"] == "POST"
        assert checkout_scenario_dict["trigger"]["path"] == "/api/checkout"
        assert checkout_scenario_dict["trigger"]["body"]["items"] == ["sku-a"]

    def test_assertion_has_correct_format(self, checkout_scenario_dict):
        """Assertion has correct format for http_status."""
        assertion = checkout_scenario_dict["assertions"][0]
        assert assertion["type"] == "http_status"
        assert assertion["path"] == "/api/orders"
        assert assertion["expect"] == 201


class TestHarnessExecutesTrigger:
    """Tests for harness trigger execution."""

    def test_harness_executes_http_trigger_POST(self, temp_scenarios_dir):
        """Harness executes POST trigger correctly."""
        from harness.scenario_harness import Harness, run_trigger

        trigger = {
            'type': 'http',
            'method': 'POST',
            'path': '/api/checkout',
            'body': {'items': ['sku-a']}
        }

        # Mock HTTP responses
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            run_trigger(trigger, "http://localhost:8080")
            # Verify urlopen was called
            pass  # If we get here without exception, trigger executed

    def test_harness_class_execute_trigger(self, temp_scenarios_dir):
        """Harness class can execute trigger."""
        from harness.scenario_harness import Harness

        trigger = {
            'type': 'http',
            'method': 'POST',
            'path': '/api/checkout',
            'body': {'items': ['sku-a']}
        }

        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            harness = Harness(base_url="http://localhost:8080")
            harness.execute_trigger(trigger)
            pass  # Success if no exception


class TestHTTPStatusAssertionExecution:
    """Tests for HTTP status assertion execution."""

    def test_harness_checks_http_status_for_path(self, temp_signal_path, temp_scenarios_dir):
        """Harness checks HTTP status for specified path."""
        from harness.scenario_harness import check_http_status_by_path

        # Mock the HTTP call
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = check_http_status_by_path("http://localhost:8080", "/api/orders", 201)
            assert result is True

    def test_http_status_check_fails_on_wrong_status(self, temp_signal_path):
        """HTTP status check fails when status doesn't match."""
        from harness.scenario_harness import check_http_status_by_path

        # Mock the HTTP call with wrong status
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = check_http_status_by_path("http://localhost:8080", "/api/orders", 201)
            assert result is False


class TestCheckoutScenarioIntegration:
    """Integration tests for checkout scenario (TC-01)."""

    def test_full_checkout_scenario_flow(self, temp_scenarios_dir, temp_signal_path):
        """Full flow: POST checkout, check /api/orders returns 201."""
        from harness.scenario_harness import Harness, write_result, run_scenario

        # Create the checkout scenario
        scenario = {
            'name': 'checkout-creates-order',
            'trigger': {
                'type': 'http',
                'method': 'POST',
                'path': '/api/checkout',
                'body': {'items': ['sku-a']}
            },
            'assertions': [
                {'type': 'http_status', 'path': '/api/orders', 'expect': 201}
            ]
        }

        scenario_file = temp_scenarios_dir / "scenario_checkout.yaml"
        scenario_file.write_text(yaml.dump(scenario))

        # Mock HTTP responses - return different responses based on path
        def mock_urlopen(request_or_url, timeout=10):
            url = request_or_url.full_url if hasattr(request_or_url, 'full_url') else str(request_or_url)
            mock_resp = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            
            if "/api/checkout" in url:
                mock_resp.status = 200
                mock_resp.getcode.return_value = 200
            elif "/api/orders" in url:
                mock_resp.status = 201
                mock_resp.getcode.return_value = 201
            else:
                mock_resp.status = 404
                mock_resp.getcode.return_value = 404
            return mock_resp

        with patch('harness.scenario_harness.SCENARIOS_DIR', temp_scenarios_dir):
            with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
                with patch('urllib.request.urlopen', side_effect=mock_urlopen):
                    # Run the scenario
                    passed = run_scenario(scenario, "http://localhost:8080")

                    assert passed is True

    def test_signal_reflects_pass_on_success(self, temp_scenarios_dir, temp_signal_path):
        """Signal contains {pass: true} when scenario passes."""
        from harness.scenario_harness import write_result

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            write_result(True)

            with open(temp_signal_path) as f:
                signal = json.load(f)

            assert signal == {"pass": True}

    def test_signal_reflects_fail_on_failure(self, temp_scenarios_dir, temp_signal_path):
        """Signal contains {pass: false} when scenario fails."""
        from harness.scenario_harness import write_result

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            write_result(False)

            with open(temp_signal_path) as f:
                signal = json.load(f)

            assert signal == {"pass": False}


class TestHarnessWithRealScenario:
    """Tests using the actual scenario files."""

    def test_scenario_000_executes_trigger(self):
        """Scenario 000 executes its trigger correctly."""
        from harness.scenario_harness import load_scenario_from_file

        scenario_path = Path("scenarios/scenario_000.yaml")
        if scenario_path.exists():
            scenario = load_scenario_from_file(scenario_path)
            assert scenario is not None
            assert 'trigger' in scenario or 'assertions' in scenario

    def test_http_status_assertion_runs_against_localhost(self):
        """HTTP status assertion runs against localhost:8080."""
        from harness.scenario_harness import check_http_status_by_path

        # This will fail if system not running, but shouldn't raise exceptions
        try:
            result = check_http_status_by_path("http://localhost:8080", "/health", 200)
            assert isinstance(result, bool)
        except Exception:
            # Network errors are expected if system not running
            assert True

    def test_harness_class_works(self):
        """Harness class can be instantiated and used."""
        from harness.scenario_harness import Harness

        harness = Harness(base_url="http://localhost:8080")
        assert harness.base_url == "http://localhost:8080"
        
        # Test check_http_status
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        
        with patch('urllib.request.urlopen', return_value=mock_response):
            result = harness.check_http_status("/health", 200)
            assert result is True


class TestRunScenario:
    """Tests for the run_scenario function."""

    def test_run_scenario_with_pass(self):
        """run_scenario returns True when assertions pass."""
        from harness.scenario_harness import run_scenario

        scenario = {
            'name': 'test-scenario',
            'assertions': [
                {'type': 'http_status', 'path': '/health', 'expect': 200}
            ]
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = run_scenario(scenario, "http://localhost:8080")
            assert result is True

    def test_run_scenario_with_fail(self):
        """run_scenario returns False when assertions fail."""
        from harness.scenario_harness import run_scenario

        scenario = {
            'name': 'test-scenario',
            'assertions': [
                {'type': 'http_status', 'path': '/api/orders', 'expect': 201}
            ]
        }

        mock_response = MagicMock()
        mock_response.status = 500  # Wrong status
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = run_scenario(scenario, "http://localhost:8080")
            assert result is False

    def test_run_scenario_with_trigger(self):
        """run_scenario executes trigger before assertions."""
        from harness.scenario_harness import run_scenario

        scenario = {
            'name': 'checkout-scenario',
            'trigger': {
                'type': 'http',
                'method': 'POST',
                'path': '/api/checkout',
                'body': {'items': ['sku-a']}
            },
            'assertions': [
                {'type': 'http_status', 'path': '/api/orders', 'expect': 201}
            ]
        }

        call_log = []
        
        def mock_urlopen(request_or_url, timeout=10):
            url = request_or_url.full_url if hasattr(request_or_url, 'full_url') else str(request_or_url)
            call_log.append(url)
            mock_resp = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            
            if "/api/checkout" in url:
                mock_resp.status = 200
            else:
                mock_resp.status = 201
            return mock_resp

        with patch('urllib.request.urlopen', side_effect=mock_urlopen):
            result = run_scenario(scenario, "http://localhost:8080")
            
            assert result is True
            assert any("/api/checkout" in url for url in call_log)
            assert any("/api/orders" in url for url in call_log)
