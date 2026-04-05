"""Tests for 5-scenario aggregation (TC-03 from Section 5).

Scenario: All-pass aggregation (TC-03 from Section 5)
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


class TestFiveScenarioAggregation:
    """Tests for 5-scenario all-pass aggregation."""

    @pytest.fixture
    def five_passing_scenarios(self) -> list:
        """Five scenarios that all pass."""
        return [
            {
                'name': 'scenario-1',
                'trigger': {'type': 'http', 'method': 'GET', 'path': '/api/test1'},
                'assertions': [{'type': 'http_status', 'path': '/api/test1', 'expect': 200}]
            },
            {
                'name': 'scenario-2',
                'trigger': {'type': 'http', 'method': 'GET', 'path': '/api/test2'},
                'assertions': [{'type': 'http_status', 'path': '/api/test2', 'expect': 200}]
            },
            {
                'name': 'scenario-3',
                'trigger': {'type': 'http', 'method': 'GET', 'path': '/api/test3'},
                'assertions': [{'type': 'http_status', 'path': '/api/test3', 'expect': 200}]
            },
            {
                'name': 'scenario-4',
                'trigger': {'type': 'http', 'method': 'GET', 'path': '/api/test4'},
                'assertions': [{'type': 'http_status', 'path': '/api/test4', 'expect': 200}]
            },
            {
                'name': 'scenario-5',
                'trigger': {'type': 'http', 'method': 'GET', 'path': '/api/test5'},
                'assertions': [{'type': 'http_status', 'path': '/api/test5', 'expect': 200}]
            },
        ]

    def test_five_scenarios_all_pass_signal_is_true(self, five_passing_scenarios, temp_signal_path):
        """All-pass aggregation: 5 scenarios pass -> signal is {pass: true}."""
        from harness.scenario_harness import Harness

        harness = Harness(base_url="http://localhost:8080")

        # Mock all HTTP responses as successful
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', return_value=mock_response):
                # Execute all 5 scenarios
                results = []
                for scenario in five_passing_scenarios:
                    result = harness.execute_scenario(scenario)
                    results.append(result)

                # All should pass
                assert len(results) == 5
                assert all(r['passed'] for r in results), "All scenarios should pass"

                # Write aggregated result
                all_passed = all(r['passed'] for r in results)
                from harness.scenario_harness import write_result
                write_result(all_passed)

                # Verify signal is {pass: true}
                assert temp_signal_path.exists()
                with open(temp_signal_path) as f:
                    signal = json.load(f)
                assert signal == {"pass": True}

    def test_harness_execute_all_five_scenarios(self, five_passing_scenarios, temp_scenarios_dir):
        """Harness can execute all 5 scenarios and aggregate results."""
        from harness.scenario_harness import Harness

        # Write 5 scenario files
        for i, scenario in enumerate(five_passing_scenarios):
            scenario_file = temp_scenarios_dir / f"scenario_{i+1}.yaml"
            import yaml
            scenario_file.write_text(yaml.dump(scenario))

        harness = Harness(base_url="http://localhost:8080")

        # Mock all HTTP responses as successful
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('harness.scenario_harness.SCENARIOS_DIR', temp_scenarios_dir):
            with patch('urllib.request.urlopen', return_value=mock_response):
                results = harness.execute_all()

                # Should have 5 results
                assert len(results) == 5
                # All should pass
                assert all(r['passed'] for r in results)

    def test_five_scenarios_fifth_fails_signal_is_false(self, five_passing_scenarios, temp_signal_path):
        """Any-fail aggregation: scenario 5 fails -> signal is {pass: false}."""
        from harness.scenario_harness import Harness, run_scenario, write_result

        harness = Harness(base_url="http://localhost:8080")

        call_count = [0]

        # Mock responses: first 4 succeed (8 calls = trigger+assertion for each), 5th fails
        def mock_urlopen(request, **kwargs):
            mock = MagicMock()
            call_count[0] += 1
            # Calls 1-8 are scenarios 1-4 (trigger + assertion each)
            # Calls 9-10 are scenario 5 trigger + assertion
            # After call 10, scenario 5 assertion should fail
            if call_count[0] > 8:  # Scenario 5
                mock.status = 500  # Scenario 5 fails
            else:
                mock.status = 200  # Scenarios 1-4 pass
            mock.__enter__ = MagicMock(return_value=mock)
            mock.__exit__ = MagicMock(return_value=False)
            return mock

        with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
            with patch('urllib.request.urlopen', side_effect=mock_urlopen):
                # Execute all 5 scenarios
                results = []
                for scenario in five_passing_scenarios:
                    result = harness.execute_scenario(scenario)
                    results.append(result)

                # Verify scenario 5 failed, others passed
                assert results[0]['passed'] is True
                assert results[1]['passed'] is True
                assert results[2]['passed'] is True
                assert results[3]['passed'] is True
                assert results[4]['passed'] is False

                # Write aggregated result
                all_passed = all(r['passed'] for r in results)
                write_result(all_passed)

                # Verify signal is {pass: false}
                assert temp_signal_path.exists()
                with open(temp_signal_path) as f:
                    signal = json.load(f)
                assert signal == {"pass": False}


class TestHarnessExecuteAll:
    """Tests for Harness.execute_all() method."""

    def test_execute_all_loads_and_runs_scenarios(self, temp_scenarios_dir):
        """execute_all loads all scenarios and runs them."""
        from harness.scenario_harness import Harness, load_scenarios
        import yaml

        # Create 3 simple scenarios
        for i in range(1, 4):
            scenario = {
                'name': f'scenario-{i}',
                'assertions': [{'type': 'http_status', 'path': f'/api/test{i}', 'expect': 200}]
            }
            scenario_file = temp_scenarios_dir / f"test_{i}.yaml"
            scenario_file.write_text(yaml.dump(scenario))

        harness = Harness(base_url="http://localhost:8080")

        # Mock HTTP responses
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('harness.scenario_harness.SCENARIOS_DIR', temp_scenarios_dir):
            with patch('urllib.request.urlopen', return_value=mock_response):
                results = harness.execute_all()

                assert len(results) == 3
                assert all(r['passed'] for r in results)

    def test_execute_all_aggregates_results(self, temp_scenarios_dir, temp_signal_path):
        """execute_all aggregates results and writes signal."""
        from harness.scenario_harness import Harness, load_scenarios
        import yaml

        # Create 3 passing scenarios
        for i in range(1, 4):
            scenario = {
                'name': f'scenario-{i}',
                'assertions': [{'type': 'http_status', 'path': f'/api/test{i}', 'expect': 200}]
            }
            scenario_file = temp_scenarios_dir / f"test_{i}.yaml"
            scenario_file.write_text(yaml.dump(scenario))

        harness = Harness(base_url="http://localhost:8080")

        # Mock HTTP responses
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('harness.scenario_harness.SCENARIOS_DIR', temp_scenarios_dir):
            with patch('harness.scenario_harness.SIGNAL_FILE', temp_signal_path):
                with patch('urllib.request.urlopen', return_value=mock_response):
                    results = harness.execute_all()

                    # All pass -> signal should be {pass: true}
                    all_passed = all(r['passed'] for r in results)
                    from harness.scenario_harness import write_result
                    write_result(all_passed)

                    with open(temp_signal_path) as f:
                        signal = json.load(f)
                    assert signal == {"pass": True}
