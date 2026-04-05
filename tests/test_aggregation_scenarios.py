"""Tests for scenario aggregation behavior - TC-03 and TC-04 from Section 5.

Scenario TC-03 (All-pass aggregation):
Given 5 scenarios execute
And scenarios 1-4 assertions pass
And scenario 5 assertions pass
When harness writes signal
Then signal is { "pass": true }

Scenario TC-04 (Any-fail aggregation):
Given 5 scenarios execute
And scenarios 1-4 assertions pass
And scenario 5 assertions fail
When harness writes signal
Then signal is { "pass": false }
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
import urllib.error


def make_success_response(*args, **kwargs):
    """Create a mock successful HTTP response."""
    mock = MagicMock()
    mock.status = 200
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def make_error_response(code):
    """Create a mock HTTP error response."""
    return urllib.error.HTTPError(
        url='http://localhost:8080/api/test',
        code=code,
        msg='Error',
        hdrs={},
        fp=None
    )


class TestAllPassAggregation:
    """Tests for TC-03: All scenarios pass aggregation."""

    @pytest.fixture
    def five_passing_scenarios(self) -> list[dict]:
        """Five scenarios, all with passing assertions."""
        return [
            {'name': 'scenario_001', 'assertions': [{'type': 'http_status', 'path': '/api/health', 'expect': 200}]},
            {'name': 'scenario_002', 'assertions': [{'type': 'http_status', 'path': '/api/users', 'expect': 200}]},
            {'name': 'scenario_003', 'assertions': [{'type': 'http_status', 'path': '/api/orders', 'expect': 200}]},
            {'name': 'scenario_004', 'assertions': [{'type': 'http_status', 'path': '/api/products', 'expect': 200}]},
            {'name': 'scenario_005', 'assertions': [{'type': 'http_status', 'path': '/api/cart', 'expect': 200}]},
        ]

    def test_all_pass_signal_is_true(self, five_passing_scenarios, temp_signal_path):
        """When all 5 scenarios pass, signal is {pass: true}."""
        from harness.scenario_harness import Harness, write_result

        harness = Harness(base_url="http://localhost:8080")

        # Mock successful HTTP responses for all assertions
        mock_response = make_success_response()

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('harness.scenario_harness.urllib.request.urlopen', return_value=mock_response):
                # Execute all scenarios
                results = []
                for scenario in five_passing_scenarios:
                    result = harness.execute_scenario(scenario)
                    results.append(result)

                # All should pass
                assert all(r['passed'] for r in results)

                # Signal should be pass: true
                all_passed = all(r['passed'] for r in results)
                write_result(all_passed)

                with open(temp_signal_path) as f:
                    signal = json.load(f)
                assert signal == {"pass": True}

    def test_harness_execute_all_returns_all_results(self, five_passing_scenarios, temp_scenarios_dir):
        """Harness.execute_all returns results for all scenarios."""
        from harness.scenario_harness import Harness

        # Write scenario files
        for i, scenario in enumerate(five_passing_scenarios):
            scenario_file = temp_scenarios_dir / f"scenario_{i:03d}.yaml"
            scenario_file.write_text(yaml.dump(scenario))

        harness = Harness(base_url="http://localhost:8080")

        # Mock successful HTTP responses
        mock_response = make_success_response()

        with patch('harness.scenario_harness.SCENARIOS_DIR', temp_scenarios_dir):
            with patch('harness.scenario_harness.urllib.request.urlopen', return_value=mock_response):
                results = harness.execute_all()
                assert len(results) == 5
                assert all(r['passed'] for r in results)


class TestAnyFailAggregation:
    """Tests for TC-04: Any-fail aggregation (the main scenario from the task)."""

    @pytest.fixture
    def five_scenarios_last_fails(self) -> list[dict]:
        """Five scenarios, first 4 pass, last one fails."""
        return [
            {'name': 'scenario_001', 'assertions': [{'type': 'http_status', 'path': '/api/health', 'expect': 200}]},
            {'name': 'scenario_002', 'assertions': [{'type': 'http_status', 'path': '/api/users', 'expect': 200}]},
            {'name': 'scenario_003', 'assertions': [{'type': 'http_status', 'path': '/api/orders', 'expect': 200}]},
            {'name': 'scenario_004', 'assertions': [{'type': 'http_status', 'path': '/api/products', 'expect': 200}]},
            {'name': 'scenario_005', 'assertions': [{'type': 'http_status', 'path': '/api/cart', 'expect': 201}]},  # Fails! (mock returns 500)
        ]

    def test_scenario_5_fails_signal_is_false(self, five_scenarios_last_fails, temp_signal_path):
        """When scenario 5 fails, signal is {pass: false}."""
        from harness.scenario_harness import Harness, write_result

        harness = Harness(base_url="http://localhost:8080")

        # Track which call we're on
        call_count = [0]

        # Each scenario has no trigger, only 1 assertion call per scenario
        # For 5 scenarios: 5 total calls
        # Scenarios 1-4 (calls 1-4): expect 200, get 200 = pass
        # Scenario 5 (call 5): expects 201, gets 200 = fail
        def mock_urlopen(request):
            call_count[0] += 1
            # All calls return 200 success
            return make_success_response()

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', side_effect=mock_urlopen):
                # Execute all scenarios
                results = []
                for scenario in five_scenarios_last_fails:
                    result = harness.execute_scenario(scenario)
                    results.append(result)

                # Verify: first 4 pass (expect 200, get 200), last fails (expects 201, gets 200)
                assert results[0]['passed'] is True, f"Scenario 1 failed: {results[0]}"
                assert results[1]['passed'] is True, f"Scenario 2 failed: {results[1]}"
                assert results[2]['passed'] is True, f"Scenario 3 failed: {results[2]}"
                assert results[3]['passed'] is True, f"Scenario 4 failed: {results[3]}"
                assert results[4]['passed'] is False, f"Scenario 5 should have failed: {results[4]}"

                # Signal should be pass: false
                all_passed = all(r['passed'] for r in results)
                write_result(all_passed)

                with open(temp_signal_path) as f:
                    signal = json.load(f)
                assert signal == {"pass": False}

    def test_scenario_5_failure_details_not_leaked(self, five_scenarios_last_fails, temp_signal_path):
        """Signal does not leak which scenario failed or why."""
        from harness.scenario_harness import Harness, write_result

        harness = Harness(base_url="http://localhost:8080")

        # Each scenario has no trigger, only 1 assertion call per scenario
        # Scenarios 1-4 pass, scenario 5 fails due to status mismatch
        def mock_urlopen(request):
            return make_success_response()

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', side_effect=mock_urlopen):
                # Execute all scenarios
                results = []
                for scenario in five_scenarios_last_fails:
                    result = harness.execute_scenario(scenario)
                    results.append(result)

                all_passed = all(r['passed'] for r in results)
                write_result(all_passed)

                # Read signal and verify no leakage
                with open(temp_signal_path) as f:
                    content = f.read()

                signal = json.loads(content)

                # Signal should only have 'pass' key
                assert list(signal.keys()) == ["pass"]

                # Should not contain scenario name, error details, etc.
                assert "scenario" not in signal
                assert "error" not in signal
                assert "message" not in signal
                assert "detail" not in signal
                assert "failed_scenario" not in signal

    def test_first_scenario_failure_also_fails_all(self, temp_signal_path):
        """When first scenario fails, signal is also {pass: false}."""
        from harness.scenario_harness import Harness, write_result

        harness = Harness(base_url="http://localhost:8080")

        scenarios = [
            {'name': 'scenario_001', 'assertions': [{'type': 'http_status', 'path': '/api/health', 'expect': 500}]},  # Fails!
            {'name': 'scenario_002', 'assertions': [{'type': 'http_status', 'path': '/api/users', 'expect': 200}]},
            {'name': 'scenario_003', 'assertions': [{'type': 'http_status', 'path': '/api/orders', 'expect': 200}]},
        ]

        # Each scenario has no trigger, only 1 assertion call per scenario
        # All return 200 success responses
        def mock_urlopen(request):
            return make_success_response()

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', side_effect=mock_urlopen):
                results = []
                for scenario in scenarios:
                    result = harness.execute_scenario(scenario)
                    results.append(result)

                # Verify: first fails (expects 500, got 200), rest pass (expect 200, get 200)
                assert results[0]['passed'] is False, f"Scenario 1 should have failed: {results[0]}"
                assert results[1]['passed'] is True
                assert results[2]['passed'] is True

                # Signal should still be pass: false
                all_passed = all(r['passed'] for r in results)
                write_result(all_passed)

                with open(temp_signal_path) as f:
                    signal = json.load(f)
                assert signal == {"pass": False}


class TestAggregationEdgeCases:
    """Edge cases for scenario aggregation."""

    def test_empty_scenarios_returns_pass(self, temp_signal_path):
        """Empty scenario list returns pass: true."""
        from harness.scenario_harness import Harness, write_result

        harness = Harness(base_url="http://localhost:8080")

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('harness.scenario_harness.SCENARIOS_DIR', Path('/nonexistent')):
                results = harness.execute_all()

                # Empty list = all pass
                all_passed = all(r['passed'] for r in results) if results else True
                write_result(all_passed)

                with open(temp_signal_path) as f:
                    signal = json.load(f)
                assert signal == {"pass": True}

    def test_single_passing_scenario(self, temp_signal_path):
        """Single passing scenario returns pass: true."""
        from harness.scenario_harness import Harness, write_result

        harness = Harness(base_url="http://localhost:8080")

        scenario = {'name': 'single', 'assertions': [{'type': 'http_status', 'path': '/api/health', 'expect': 200}]}

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', return_value=make_success_response()):
                result = harness.execute_scenario(scenario)
                all_passed = result['passed']
                write_result(all_passed)

                with open(temp_signal_path) as f:
                    signal = json.load(f)
                assert signal == {"pass": True}

    def test_single_failing_scenario(self, temp_signal_path):
        """Single failing scenario returns pass: false."""
        from harness.scenario_harness import Harness, write_result

        harness = Harness(base_url="http://localhost:8080")

        scenario = {'name': 'single', 'assertions': [{'type': 'http_status', 'path': '/api/health', 'expect': 500}]}

        # Scenario expects 500, server returns 200, so assertion fails
        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', return_value=make_success_response()):
                result = harness.execute_scenario(scenario)
                all_passed = result['passed']
                write_result(all_passed)

                with open(temp_signal_path) as f:
                    signal = json.load(f)
                assert signal == {"pass": False}
