"""Tests for HTTP status assertion with trigger execution (TC-01 from Section 5).

Scenario: HTTP status assertion (TC-01 from Section 5)
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
from unittest.mock import MagicMock, patch, Mock, ANY

import pytest
import yaml


class TestCheckoutScenarioDefinition:
    """Tests for checkout scenario definition."""

    @pytest.fixture
    def checkout_scenario_dict(self) -> dict:
        """Checkout scenario as dict matching SPEC.md requirements."""
        return {
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

    def test_checkout_scenario_has_post_trigger(self, checkout_scenario_dict):
        """Checkout scenario has POST trigger to /api/checkout."""
        trigger = checkout_scenario_dict['trigger']
        assert trigger['type'] == 'http'
        assert trigger['method'] == 'POST'
        assert trigger['path'] == '/api/checkout'
        assert trigger['body']['items'] == ['sku-a']

    def test_checkout_scenario_has_http_status_assertion(self, checkout_scenario_dict):
        """Checkout scenario has http_status assertion for /api/orders expecting 201."""
        assertion = checkout_scenario_dict['assertions'][0]
        assert assertion['type'] == 'http_status'
        assert assertion['path'] == '/api/orders'
        assert assertion['expect'] == 201


class TestHarnessHTTPStatusAssertion:
    """Tests for HTTP status assertion in harness."""

    def test_check_http_status_returns_true_on_matching_status(self):
        """check_http_status returns True when response status matches expected."""
        from harness.scenario_harness import check_http_status

        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = check_http_status("http://localhost:8080/api/orders", 201)
            assert result is True

    def test_check_http_status_returns_false_on_mismatched_status(self):
        """check_http_status returns False when response status doesn't match."""
        from harness.scenario_harness import check_http_status

        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = check_http_status("http://localhost:8080/api/orders", 201)
            assert result is False

    def test_check_http_status_returns_false_on_network_error(self):
        """check_http_status returns False on network error."""
        from harness.scenario_harness import check_http_status
        import urllib.error

        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("Connection refused")):
            result = check_http_status("http://localhost:8080/api/orders", 201)
            assert result is False

    def test_check_http_status_by_path_builds_correct_url(self):
        """check_http_status_by_path builds correct URL from base_url and path."""
        from harness.scenario_harness import check_http_status_by_path

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            result = check_http_status_by_path("http://localhost:8080", "/api/health", 200)
            
            mock_urlopen.assert_called_once()
            call_url = mock_urlopen.call_args[0][0]
            assert call_url == "http://localhost:8080/api/health"
            assert result is True


class TestHarnessRunTrigger:
    """Tests for harness run_trigger function."""

    def test_run_trigger_sends_post_request(self):
        """run_trigger sends POST request to specified path."""
        from harness.scenario_harness import run_trigger

        trigger = {
            'type': 'http',
            'method': 'POST',
            'path': '/api/checkout',
            'body': {'items': ['sku-a']}
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            run_trigger(trigger, "http://localhost:8080")
            
            mock_urlopen.assert_called_once()
            request = mock_urlopen.call_args[0][0]
            assert request.method == 'POST'
            assert '/api/checkout' in request.full_url

    def test_run_trigger_sends_get_request(self):
        """run_trigger sends GET request when no body."""
        from harness.scenario_harness import run_trigger

        trigger = {
            'type': 'http',
            'method': 'GET',
            'path': '/api/health'
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            run_trigger(trigger, "http://localhost:8080")
            
            mock_urlopen.assert_called_once()
            request = mock_urlopen.call_args[0][0]
            assert request.method == 'GET'

    def test_run_trigger_handles_http_error(self):
        """run_trigger handles HTTP errors gracefully."""
        from harness.scenario_harness import run_trigger
        import urllib.error

        trigger = {
            'type': 'http',
            'method': 'POST',
            'path': '/api/checkout',
            'body': {'items': ['sku-a']}
        }

        with patch('urllib.request.urlopen', side_effect=urllib.error.HTTPError(
            'http://localhost:8080/api/checkout', 500, 'Server Error', {}, None
        )):
            # Should not raise
            run_trigger(trigger, "http://localhost:8080")


class TestHarnessRunScenario:
    """Tests for harness run_scenario function."""

    def test_run_scenario_returns_true_when_assertions_pass(self, temp_signal_path):
        """run_scenario returns True when all assertions pass."""
        from harness.scenario_harness import run_scenario

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

        # Mock checkout response (trigger)
        mock_checkout_response = MagicMock()
        mock_checkout_response.status = 200
        mock_checkout_response.__enter__ = MagicMock(return_value=mock_checkout_response)
        mock_checkout_response.__exit__ = MagicMock(return_value=False)

        # Mock orders response (assertion)
        mock_orders_response = MagicMock()
        mock_orders_response.status = 201
        mock_orders_response.__enter__ = MagicMock(return_value=mock_orders_response)
        mock_orders_response.__exit__ = MagicMock(return_value=False)

        call_count = [0]
        def mock_urlopen(request, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_checkout_response
            return mock_orders_response

        with patch('urllib.request.urlopen', side_effect=mock_urlopen):
            result = run_scenario(scenario, "http://localhost:8080")
            assert result is True

    def test_run_scenario_returns_false_when_assertions_fail(self, temp_signal_path):
        """run_scenario returns False when assertions fail."""
        from harness.scenario_harness import run_scenario

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

        # Mock checkout response (trigger)
        mock_checkout_response = MagicMock()
        mock_checkout_response.status = 200
        mock_checkout_response.__enter__ = MagicMock(return_value=mock_checkout_response)
        mock_checkout_response.__exit__ = MagicMock(return_value=False)

        # Mock orders response with wrong status (assertion fails)
        mock_orders_response = MagicMock()
        mock_orders_response.status = 404
        mock_orders_response.__enter__ = MagicMock(return_value=mock_orders_response)
        mock_orders_response.__exit__ = MagicMock(return_value=False)

        call_count = [0]
        def mock_urlopen(request, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_checkout_response
            return mock_orders_response

        with patch('urllib.request.urlopen', side_effect=mock_urlopen):
            result = run_scenario(scenario, "http://localhost:8080")
            assert result is False


class TestSignalWriting:
    """Tests for signal writing."""

    def test_write_result_writes_pass_true(self, temp_signal_path):
        """write_result writes {'pass': true} to signal file."""
        from harness.scenario_harness import write_result

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            write_result(True)
            
            assert temp_signal_path.exists()
            with open(temp_signal_path) as f:
                signal = json.load(f)
            assert signal == {"pass": True}

    def test_write_result_writes_pass_false(self, temp_signal_path):
        """write_result writes {'pass': false} to signal file."""
        from harness.scenario_harness import write_result

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            write_result(False)
            
            assert temp_signal_path.exists()
            with open(temp_signal_path) as f:
                signal = json.load(f)
            assert signal == {"pass": False}

    def test_signal_contains_only_pass_field(self, temp_signal_path):
        """Signal contains only pass field - no extra data (leak prevention)."""
        from harness.scenario_harness import write_result

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            write_result(False)
            
            with open(temp_signal_path) as f:
                content = f.read()
            
            # Should be exactly {"pass": false}
            assert content == '{"pass": false}'
            
            # Verify no scenario names, errors, or details
            signal = json.loads(content)
            assert list(signal.keys()) == ["pass"]


class TestHarnessRunAssertion:
    """Tests for harness run_assertion function."""

    def test_run_assertion_handles_http_status_assertion_with_path(self):
        """run_assertion handles http_status assertion with path format."""
        from harness.scenario_harness import run_assertion

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        assertion = {
            'type': 'http_status',
            'path': '/api/orders',
            'expect': 201
        }

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = run_assertion(assertion, "http://localhost:8080")
            assert result is True

    def test_run_assertion_returns_false_on_unknown_type(self):
        """run_assertion returns False for unknown assertion types."""
        from harness.scenario_harness import run_assertion

        assertion = {
            'type': 'unknown_type',
            'some_field': 'value'
        }

        result = run_assertion(assertion, "http://localhost:8080")
        assert result is False


class TestHarnessClass:
    """Tests for the Harness class."""

    def test_harness_execute_trigger(self):
        """Harness.execute_trigger calls run_trigger."""
        from harness.scenario_harness import Harness

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        harness = Harness(base_url="http://localhost:8080")

        trigger = {
            'type': 'http',
            'method': 'POST',
            'path': '/api/checkout',
            'body': {'items': ['sku-a']}
        }

        with patch('urllib.request.urlopen', return_value=mock_response):
            harness.execute_trigger(trigger)

    def test_harness_check_http_status(self):
        """Harness.check_http_status checks status at path."""
        from harness.scenario_harness import Harness

        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        harness = Harness(base_url="http://localhost:8080")

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = harness.check_http_status("/api/orders", 201)
            assert result is True

    def test_harness_execute_scenario(self):
        """Harness.execute_scenario runs scenario and returns result."""
        from harness.scenario_harness import Harness

        scenario = {
            'name': 'test-scenario',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/api/health'
            },
            'assertions': [
                {'type': 'http_status', 'path': '/api/health', 'expect': 200}
            ]
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        harness = Harness(base_url="http://localhost:8080")

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = harness.execute_scenario(scenario)
            assert result['name'] == 'test-scenario'
            assert result['passed'] is True


class TestFullCheckoutScenarioFlow:
    """Integration tests for full checkout scenario flow."""

    def test_checkout_scenario_full_flow_with_signal(self, temp_signal_path, temp_scenarios_dir):
        """Full flow: POST checkout, check /api/orders returns 201, signal written."""
        from harness.scenario_harness import write_result, run_scenario

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

        # Mock checkout response (trigger)
        mock_checkout_response = MagicMock()
        mock_checkout_response.status = 200
        mock_checkout_response.__enter__ = MagicMock(return_value=mock_checkout_response)
        mock_checkout_response.__exit__ = MagicMock(return_value=False)

        # Mock orders response (assertion)
        mock_orders_response = MagicMock()
        mock_orders_response.status = 201
        mock_orders_response.__enter__ = MagicMock(return_value=mock_orders_response)
        mock_orders_response.__exit__ = MagicMock(return_value=False)

        call_count = [0]
        def mock_urlopen(request, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_checkout_response
            return mock_orders_response

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', side_effect=mock_urlopen):
                # Run the scenario
                passed = run_scenario(scenario, "http://localhost:8080")
                
                # Write signal
                write_result(passed)
                
                # Verify signal
                assert temp_signal_path.exists()
                with open(temp_signal_path) as f:
                    signal = json.load(f)
                assert signal == {"pass": True}
