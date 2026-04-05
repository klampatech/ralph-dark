"""Tests for TC-03: 5 scenarios execute, scenarios 1-4 pass, scenario 5 passes -> signal is {pass: true}.

Per SPEC.md Scenario: All-pass aggregation (TC-03 from Section 5)
Given 5 scenarios execute
And scenarios 1-4 assertions pass
And scenario 5 assertions pass
When harness writes signal
Then signal is { "pass": true }
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


@pytest.fixture
def five_scenarios_all_pass() -> list[dict]:
    """Five scenarios, all with passing assertions."""
    return [
        {'name': 'scenario-1', 'assertions': [{'type': 'http_status', 'path': '/api/health', 'expect': 200}]},
        {'name': 'scenario-2', 'assertions': [{'type': 'http_status', 'path': '/api/users', 'expect': 200}]},
        {'name': 'scenario-3', 'assertions': [{'type': 'http_status', 'path': '/api/orders', 'expect': 200}]},
        {'name': 'scenario-4', 'assertions': [{'type': 'http_status', 'path': '/api/products', 'expect': 200}]},
        {'name': 'scenario-5', 'assertions': [{'type': 'http_status', 'path': '/api/cart', 'expect': 200}]},
    ]


class TestFiveScenarioAllPassAggregation:
    """Tests for TC-03: All 5 scenarios pass -> signal is {pass: true}."""

    def test_five_scenarios_all_pass_signal_is_true(self, five_scenarios_all_pass, temp_signal_path, temp_scenarios_dir):
        """When all 5 scenarios pass, signal is {pass: true}."""
        from harness.scenario_harness import Harness, write_result

        # Write scenario files
        for i, scenario in enumerate(five_scenarios_all_pass):
            scenario_file = temp_scenarios_dir / f"scenario_{i+1}.yaml"
            scenario_file.write_text(yaml.dump(scenario))

        harness = Harness(base_url="http://localhost:8080")

        # Mock HTTP response with status 200
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('harness.scenario_harness.SCENARIOS_DIR', temp_scenarios_dir):
                with patch('harness.scenario_harness.urllib.request.urlopen', return_value=mock_response):
                    # Execute all scenarios
                    results = harness.execute_all()

                    # All 5 should pass
                    assert len(results) == 5
                    assert all(r['passed'] for r in results), f"Not all passed: {results}"

                    # Write aggregated result
                    all_passed = all(r['passed'] for r in results)
                    write_result(all_passed)

                    # Verify signal is {pass: true}
                    assert temp_signal_path.exists()
                    with open(temp_signal_path) as f:
                        signal = json.load(f)
                    assert signal == {"pass": True}, f"Expected {{pass: True}}, got {signal}"

    def test_five_scenarios_individual_results_correct(self, temp_signal_path, temp_scenarios_dir):
        """Verify each of the 5 scenarios has correct individual result."""
        from harness.scenario_harness import Harness

        scenarios = [
            {'name': 'scenario-1', 'assertions': [{'type': 'http_status', 'path': '/api/health', 'expect': 200}]},
            {'name': 'scenario-2', 'assertions': [{'type': 'http_status', 'path': '/api/users', 'expect': 200}]},
            {'name': 'scenario-3', 'assertions': [{'type': 'http_status', 'path': '/api/orders', 'expect': 200}]},
            {'name': 'scenario-4', 'assertions': [{'type': 'http_status', 'path': '/api/products', 'expect': 200}]},
            {'name': 'scenario-5', 'assertions': [{'type': 'http_status', 'path': '/api/cart', 'expect': 200}]},
        ]

        # Write scenario files
        for i, scenario in enumerate(scenarios):
            scenario_file = temp_scenarios_dir / f"scenario_{i+1}.yaml"
            scenario_file.write_text(yaml.dump(scenario))

        harness = Harness(base_url="http://localhost:8080")

        # Mock HTTP response with status 200
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('harness.scenario_harness.SCENARIOS_DIR', temp_scenarios_dir):
            with patch('harness.scenario_harness.urllib.request.urlopen', return_value=mock_response):
                results = harness.execute_all()

                # Each scenario should pass
                for i, result in enumerate(results):
                    assert result['passed'] is True, f"Scenario {i+1} should have passed: {result}"
                    assert result['name'] == f'scenario-{i+1}'

    def test_aggregated_result_true_when_all_pass(self, temp_signal_path, temp_scenarios_dir):
        """Aggregated result is True when all scenarios pass."""
        from harness.scenario_harness import Harness, write_result

        scenarios = [
            {'name': 'scenario-1', 'assertions': [{'type': 'http_status', 'path': '/api/health', 'expect': 200}]},
            {'name': 'scenario-2', 'assertions': [{'type': 'http_status', 'path': '/api/users', 'expect': 200}]},
            {'name': 'scenario-3', 'assertions': [{'type': 'http_status', 'path': '/api/orders', 'expect': 200}]},
            {'name': 'scenario-4', 'assertions': [{'type': 'http_status', 'path': '/api/products', 'expect': 200}]},
            {'name': 'scenario-5', 'assertions': [{'type': 'http_status', 'path': '/api/cart', 'expect': 200}]},
        ]

        # Write scenario files
        for i, scenario in enumerate(scenarios):
            scenario_file = temp_scenarios_dir / f"scenario_{i+1}.yaml"
            scenario_file.write_text(yaml.dump(scenario))

        harness = Harness(base_url="http://localhost:8080")

        # Mock HTTP response with status 200
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('harness.scenario_harness.SCENARIOS_DIR', temp_scenarios_dir):
                with patch('harness.scenario_harness.urllib.request.urlopen', return_value=mock_response):
                    results = harness.execute_all()
                    
                    # All pass
                    all_passed = all(r['passed'] for r in results)
                    assert all_passed is True
                    
                    # Write result
                    write_result(all_passed)
                    
                    # Read signal
                    with open(temp_signal_path) as f:
                        signal = json.load(f)
                    
                    assert signal == {"pass": True}
