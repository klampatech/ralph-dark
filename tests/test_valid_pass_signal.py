"""Tests for Scenario TC-01 from Section 6: Valid pass signal.

Given harness executed with all scenarios passing
When harness writes the signal file
Then /tmp/ralph-scenario-result.json contains exactly { "pass": true }
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml


class TestValidPassSignal:
    """Tests for TC-01 from Section 6: Valid pass signal."""

    def test_harness_writes_valid_pass_signal_file(self, tmp_path):
        """Harness writes signal file containing exactly { "pass": true }."""
        # Create temporary scenarios directory with a passing scenario
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create a scenario with no assertions (harness treats no assertions as pass)
        scenario = {
            'name': 'always-pass',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/health'
            }
            # No assertions means pass
        }
        scenario_file = scenarios_dir / "test.yaml"
        scenario_file.write_text(yaml.dump(scenario))
        
        # Run the harness
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        # Verify harness executed successfully
        assert result.returncode == 0, f"Harness failed: {result.stderr}"
        
        # Verify signal file exists
        assert signal_file.exists(), f"Signal file not created at {signal_file}"
        
        # Read and verify signal content
        content = signal_file.read_text()
        signal = json.loads(content)
        
        # Verify exactly { "pass": true }
        assert signal == {"pass": True}, f"Expected {{'pass': true}}, got {signal}"
        
        # Verify no extra keys
        assert list(signal.keys()) == ["pass"]
        
        # Verify value is boolean true
        assert signal["pass"] is True

    def test_signal_file_is_valid_json_no_extra_whitespace(self, tmp_path):
        """Signal file contains valid JSON with no extra whitespace."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # No scenarios should result in pass=true
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert signal_file.exists()
        
        # Content should be exactly {"pass": true}
        content = signal_file.read_text().strip()
        assert content == '{"pass": true}'
        
        # Verify it parses correctly
        signal = json.loads(content)
        assert signal == {"pass": True}

    def test_signal_no_leaky_data_on_pass(self, tmp_path):
        """Signal on pass contains no scenario names, errors, or details."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create a named scenario with no assertions
        scenario = {
            'name': 'my-important-scenario',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/api/test'
            }
            # No assertions means pass
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
        
        # Must have pass:true
        assert signal == {"pass": True}


class TestHarnessPassAggregation:
    """Tests for harness all-pass aggregation."""

    def test_multiple_passing_scenarios_result_in_pass_true(self, tmp_path):
        """Multiple passing scenarios aggregate to { pass: true }."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create multiple scenarios with no assertions
        for i in range(3):
            scenario = {
                'name': f'passing-scenario-{i}',
                'trigger': {
                    'type': 'http',
                    'method': 'GET',
                    'path': f'/api/{i}'
                }
                # No assertions means pass
            }
            scenario_file = scenarios_dir / f"scenario_{i}.yaml"
            scenario_file.write_text(yaml.dump(scenario))
        
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        signal = json.loads(signal_file.read_text())
        assert signal == {"pass": True}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])