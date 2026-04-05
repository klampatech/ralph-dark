"""Integration test for Scenario TC-01 from Section 6: Valid pass signal.

Given harness executed with all scenarios passing
When harness writes the signal file
Then /tmp/ralph-scenario-result.json contains exactly { "pass": true }
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml


class TestValidPassSignalIntegration:
    """End-to-end integration tests for the valid pass signal scenario."""

    def test_harness_all_scenarios_pass_writes_pass_true(self):
        """Scenario TC-01: Harness with all passing scenarios writes { "pass": true }."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios_dir = Path(tmpdir) / "scenarios"
            scenarios_dir.mkdir()
            signal_file = Path("/tmp/ralph-scenario-result.json")
            
            # Create a simple scenario with no assertions (passes by default)
            scenario = {
                'name': 'always-pass-test',
                'trigger': {
                    'type': 'http',
                    'method': 'GET',
                    'path': '/health'
                }
                # No assertions = pass
            }
            (scenarios_dir / "test.yaml").write_text(yaml.dump(scenario))
            
            # Run the harness shell script
            result = subprocess.run(
                ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
                capture_output=True,
                text=True
            )
            
            # Verify execution completed
            assert result.returncode == 0, f"Harness failed with: {result.stderr}"
            
            # Verify signal file exists and contains exactly {"pass": true}
            assert signal_file.exists(), f"Signal file not created at {signal_file}"
            
            content = signal_file.read_text().strip()
            signal = json.loads(content)
            
            # The signal must be exactly {"pass": true}
            assert signal == {"pass": True}, f"Expected {{'pass': True}}, got {signal}"
            
            # Ensure no extra fields
            assert list(signal.keys()) == ["pass"], "Signal must have only 'pass' key"
            assert signal["pass"] is True, "Signal 'pass' must be boolean true"

    def test_signal_file_format_exactly_pass_true(self):
        """Verify the signal file is exactly { "pass": true } - no extra whitespace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios_dir = Path(tmpdir) / "scenarios"
            scenarios_dir.mkdir()
            signal_file = Path("/tmp/ralph-scenario-result.json")
            
            # Create empty scenarios directory (no scenarios = pass)
            result = subprocess.run(
                ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert signal_file.exists()
            
            # Exact JSON format check
            content = signal_file.read_text()
            assert content == '{"pass": true}', f"Expected exact JSON '{{\"pass\": true}}', got '{content}'"
            
            # Verify it's valid JSON that parses to the expected dict
            signal = json.loads(content)
            assert signal == {"pass": True}

    def test_signal_no_leaky_data(self):
        """Verify signal contains no scenario names, error messages, or details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios_dir = Path(tmpdir) / "scenarios"
            scenarios_dir.mkdir()
            signal_file = Path("/tmp/ralph-scenario-result.json")
            
            # Create a named scenario
            scenario = {
                'name': 'my-super-secret-scenario',
                'trigger': {
                    'type': 'http',
                    'method': 'POST',
                    'path': '/api/test'
                }
            }
            (scenarios_dir / "secret.yaml").write_text(yaml.dump(scenario))
            
            result = subprocess.run(
                ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
                capture_output=True,
                text=True
            )
            
            signal = json.loads(signal_file.read_text())
            
            # Ensure no leaky fields
            for forbidden in ['name', 'scenario', 'error', 'message', 'details', 'trace']:
                assert forbidden not in signal, f"Leaky field '{forbidden}' found in signal"
            
            # Must still be valid pass signal
            assert signal == {"pass": True}

    def test_multiple_passing_scenarios_aggregate_to_pass(self):
        """Verify multiple passing scenarios aggregate to { pass: true }."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios_dir = Path(tmpdir) / "scenarios"
            scenarios_dir.mkdir()
            signal_file = Path("/tmp/ralph-scenario-result.json")
            
            # Create multiple scenarios with no assertions
            for i in range(5):
                scenario = {
                    'name': f'passing-scenario-{i}',
                    'trigger': {
                        'type': 'http',
                        'method': 'GET',
                        'path': f'/endpoint-{i}'
                    }
                }
                (scenarios_dir / f"scenario_{i}.yaml").write_text(yaml.dump(scenario))
            
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