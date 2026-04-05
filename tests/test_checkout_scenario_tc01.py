"""Tests for checkout scenario (TC-01 from Section 5).

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
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestCheckoutScenarioTC01:
    """Tests for TC-01: HTTP status assertion scenario."""

    @pytest.fixture
    def checkout_scenario_dict(self) -> dict:
        """Checkout scenario as defined in SPEC.md."""
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

    def test_checkout_scenario_trigger_post_to_checkout(self, checkout_scenario_dict):
        """Scenario trigger is POST to /api/checkout with body items: [sku-a]."""
        trigger = checkout_scenario_dict['trigger']
        assert trigger['method'] == 'POST'
        assert trigger['path'] == '/api/checkout'
        assert trigger['body']['items'] == ['sku-a']

    def test_checkout_scenario_assertion_path_and_expect(self, checkout_scenario_dict):
        """Scenario assertion checks /api/orders for 201 status."""
        assertion = checkout_scenario_dict['assertions'][0]
        assert assertion['type'] == 'http_status'
        assert assertion['path'] == '/api/orders'
        assert assertion['expect'] == 201


class TestRunAssertionHandlesTypeFormat:
    """Tests for run_assertion with 'type' key format."""

    def test_run_assertion_with_type_http_status(self):
        """run_assertion handles assertion with 'type' key format."""
        from harness.scenario_harness import run_assertion

        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        # Assertion format: { "type": "http_status", "path": "/api/orders", "expect": 201 }
        assertion = {
            'type': 'http_status',
            'path': '/api/orders',
            'expect': 201
        }

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = run_assertion(assertion, "http://localhost:8080")
            assert result is True

    def test_run_assertion_with_type_fails_on_wrong_status(self):
        """run_assertion returns False when status doesn't match expected."""
        from harness.scenario_harness import run_assertion

        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        assertion = {
            'type': 'http_status',
            'path': '/api/orders',
            'expect': 201
        }

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = run_assertion(assertion, "http://localhost:8080")
            assert result is False


class TestExecuteTrigger:
    """Tests for the execute_trigger function."""

    def test_execute_trigger_sends_post_with_body(self):
        """execute_trigger sends POST request with JSON body."""
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
            assert request.full_url == "http://localhost:8080/api/checkout"
            assert request.method == 'POST'


class TestRunScenarioWithCheckout:
    """Tests for run_scenario with checkout scenario."""

    def test_run_scenario_with_checkout_trigger_and_assertion(self, temp_signal_path):
        """run_scenario executes trigger then checks assertion."""
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

        # Mock responses - checkout returns 200, orders returns 201
        mock_checkout_response = MagicMock()
        mock_checkout_response.status = 200
        mock_checkout_response.__enter__ = MagicMock(return_value=mock_checkout_response)
        mock_checkout_response.__exit__ = MagicMock(return_value=False)

        mock_orders_response = MagicMock()
        mock_orders_response.status = 201
        mock_orders_response.__enter__ = MagicMock(return_value=mock_orders_response)
        mock_orders_response.__exit__ = MagicMock(return_value=False)

        call_count = [0]
        def mock_urlopen(request, timeout=10):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_checkout_response
            return mock_orders_response

        with patch('urllib.request.urlopen', side_effect=mock_urlopen):
            result = run_scenario(scenario, "http://localhost:8080")
            assert result is True

    def test_run_scenario_returns_false_when_assertion_fails(self, temp_signal_path):
        """run_scenario returns False when assertion fails."""
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

        # Mock responses - checkout returns 200, orders returns 500 (wrong)
        mock_checkout_response = MagicMock()
        mock_checkout_response.status = 200
        mock_checkout_response.__enter__ = MagicMock(return_value=mock_checkout_response)
        mock_checkout_response.__exit__ = MagicMock(return_value=False)

        mock_orders_response = MagicMock()
        mock_orders_response.status = 500
        mock_orders_response.__enter__ = MagicMock(return_value=mock_orders_response)
        mock_orders_response.__exit__ = MagicMock(return_value=False)

        call_count = [0]
        def mock_urlopen(request, timeout=10):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_checkout_response
            return mock_orders_response

        with patch('urllib.request.urlopen', side_effect=mock_urlopen):
            result = run_scenario(scenario, "http://localhost:8080")
            assert result is False


class TestSignalReflectsPassFail:
    """Tests for signal reflecting pass/fail correctly."""

    def test_signal_reflects_pass_on_success(self, temp_signal_path):
        """Signal contains {pass: true} when scenario passes."""
        from harness.scenario_harness import write_result

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            write_result(True)

            assert temp_signal_path.exists()
            with open(temp_signal_path) as f:
                signal = json.load(f)
            assert signal == {"pass": True}

    def test_signal_reflects_fail_on_failure(self, temp_signal_path):
        """Signal contains {pass: false} when scenario fails."""
        from harness.scenario_harness import write_result

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            write_result(False)

            assert temp_signal_path.exists()
            with open(temp_signal_path) as f:
                signal = json.load(f)
            assert signal == {"pass": False}


class TestFullCheckoutScenarioFlow:
    """Integration test: full checkout scenario flow."""

    def test_full_checkout_scenario_flow_with_signal(self, temp_signal_path):
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
        def mock_urlopen(request, timeout=10):
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
