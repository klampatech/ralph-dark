"""Tests for Scenario TC-02 from Section 6: Valid fail signal.

Given harness executed with at least one scenario failing
When harness writes the signal file
Then /tmp/ralph-scenario-result.json contains exactly { "pass": false }
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml


class TestValidFailSignal:
    """Tests for TC-02 from Section 6: Valid fail signal."""

    def test_harness_writes_valid_fail_signal_file(self, tmp_path):
        """Harness writes signal file containing exactly { "pass": false } when a scenario fails."""
        # Create temporary scenarios directory with a failing scenario
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create a scenario that will fail (expecting wrong status code)
        scenario = {
            'name': 'always-fail',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/health'
            },
            'assertions': [
                {
                    'type': 'http_status',
                    'path': '/health',
                    'expect': 500  # Expect 500, but server returns 200 (or unreachable)
                }
            ]
        }
        scenario_file = scenarios_dir / "fail.yaml"
        scenario_file.write_text(yaml.dump(scenario))
        
        # Run the harness
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        # Verify harness completed execution (may still exit 0 for partial run)
        # The key is what gets written to the signal file
        
        # Verify signal file exists
        assert signal_file.exists(), f"Signal file not created at {signal_file}"
        
        # Read and verify signal content
        content = signal_file.read_text()
        signal = json.loads(content)
        
        # Verify exactly { "pass": false }
        assert signal == {"pass": False}, f"Expected {{'pass': false}}, got {signal}"
        
        # Verify no extra keys
        assert list(signal.keys()) == ["pass"]
        
        # Verify value is boolean false
        assert signal["pass"] is False

    def test_signal_file_is_valid_json_no_extra_whitespace_on_fail(self, tmp_path):
        """Signal file contains valid JSON with no extra whitespace on fail."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create a scenario that will fail
        scenario = {
            'name': 'fail-scenario',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/nonexistent'
            },
            'assertions': [
                {
                    'type': 'http_status',
                    'path': '/nonexistent',
                    'expect': 200
                }
            ]
        }
        scenario_file = scenarios_dir / "fail.yaml"
        scenario_file.write_text(yaml.dump(scenario))
        
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        assert signal_file.exists()
        
        # Content should be exactly {"pass": false}
        content = signal_file.read_text().strip()
        assert content == '{"pass": false}'
        
        # Verify it parses correctly
        signal = json.loads(content)
        assert signal == {"pass": False}

    def test_signal_no_leaky_data_on_fail(self, tmp_path):
        """Signal on fail contains no scenario names, errors, or details."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create a named scenario with a failing assertion
        scenario = {
            'name': 'my-failing-scenario',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/api/test'
            },
            'assertions': [
                {
                    'type': 'http_status',
                    'path': '/api/test',
                    'expect': 201
                }
            ]
        }
        scenario_file = scenarios_dir / "important.yaml"
        scenario_file.write_text(yaml.dump(scenario))
        
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        assert signal_file.exists()
        signal = json.loads(signal_file.read_text())
        
        # Verify no leaky fields
        assert "scenario" not in signal
        assert "name" not in signal
        assert "error" not in signal
        assert "message" not in signal
        assert "details" not in signal
        assert "assertion" not in signal
        assert "reason" not in signal
        
        # Must have pass:false
        assert signal == {"pass": False}


class TestHarnessFailAggregation:
    """Tests for harness fail aggregation (any-fail aggregation)."""

    def test_multiple_passing_one_failing_scenario_results_in_pass_false(self, tmp_path):
        """Multiple scenarios with one failing aggregates to { pass: false }."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create multiple scenarios - 2 pass, 1 fails
        # Scenario 1: pass (no assertions)
        scenario1 = {
            'name': 'passing-scenario-1',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/api/1'
            }
            # No assertions means pass
        }
        scenario_file = scenarios_dir / "scenario_1.yaml"
        scenario_file.write_text(yaml.dump(scenario1))
        
        # Scenario 2: pass (no assertions)
        scenario2 = {
            'name': 'passing-scenario-2',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/api/2'
            }
            # No assertions means pass
        }
        scenario_file = scenarios_dir / "scenario_2.yaml"
        scenario_file.write_text(yaml.dump(scenario2))
        
        # Scenario 3: fail (wrong status expected)
        scenario3 = {
            'name': 'failing-scenario-3',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/api/3'
            },
            'assertions': [
                {
                    'type': 'http_status',
                    'path': '/api/3',
                    'expect': 999  # Impossible status code to force failure
                }
            ]
        }
        scenario_file = scenarios_dir / "scenario_3.yaml"
        scenario_file.write_text(yaml.dump(scenario3))
        
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        # Signal should be pass:false even though 2 scenarios "passed"
        signal = json.loads(signal_file.read_text())
        assert signal == {"pass": False}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
