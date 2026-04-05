"""Tests for Scenario TC-02 from Section 6: Valid fail signal - REAL signal file.

Given harness executed with at least one scenario failing
When harness writes the signal file
Then /tmp/ralph-scenario-result.json contains exactly { "pass": false }

This test verifies the signal file is written to the actual location,
not a custom tmp_path.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml


SIGNAL_PATH = Path("/tmp/ralph-scenario-result.json")


@pytest.fixture(autouse=True)
def cleanup_signal_file():
    """Clean up signal file before and after each test."""
    # Clean before
    if SIGNAL_PATH.exists():
        SIGNAL_PATH.unlink()
    yield
    # Clean after
    if SIGNAL_PATH.exists():
        SIGNAL_PATH.unlink()


class TestValidFailSignalRealSignal:
    """Tests for TC-02 from Section 6: Valid fail signal to REAL signal file."""

    def test_harness_writes_pass_false_to_real_signal_file_on_failure(self):
        """Harness writes exactly { "pass": false } to /tmp/ralph-scenario-result.json when scenario fails."""
        # Create temporary scenarios directory with a failing scenario
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios_dir = Path(tmpdir) / "scenarios"
            scenarios_dir.mkdir()
            
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
            
            # Run the harness - it writes to the REAL /tmp/ralph-scenario-result.json
            result = subprocess.run(
                ['bash', '.orch/harness.sh', str(scenarios_dir), str(SIGNAL_PATH)],
                capture_output=True,
                text=True
            )
            
            # Verify signal file exists at the REAL location
            assert SIGNAL_PATH.exists(), f"Signal file not created at {SIGNAL_PATH}"
            
            # Read and verify signal content
            content = SIGNAL_PATH.read_text()
            signal = json.loads(content)
            
            # Verify exactly { "pass": false }
            assert signal == {"pass": False}, f"Expected {{'pass': false}}, got {signal}"
            
            # Verify no extra keys
            assert list(signal.keys()) == ["pass"]
            
            # Verify value is boolean false
            assert signal["pass"] is False

    def test_signal_file_exactly_pass_false_no_extra_whitespace(self):
        """Signal file contains exactly { "pass": false } with no extra whitespace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios_dir = Path(tmpdir) / "scenarios"
            scenarios_dir.mkdir()
            
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
                ['bash', '.orch/harness.sh', str(scenarios_dir), str(SIGNAL_PATH)],
                capture_output=True,
                text=True
            )
            
            assert SIGNAL_PATH.exists()
            
            # Content should be exactly {"pass": false}
            content = SIGNAL_PATH.read_text().strip()
            assert content == '{"pass": false}', f"Expected exact match, got: {content}"
            
            # Verify it parses correctly
            signal = json.loads(content)
            assert signal == {"pass": False}

    def test_signal_no_leaky_data_on_fail(self):
        """Signal on fail contains no scenario names, errors, or details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios_dir = Path(tmpdir) / "scenarios"
            scenarios_dir.mkdir()
            
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
                ['bash', '.orch/harness.sh', str(scenarios_dir), str(SIGNAL_PATH)],
                capture_output=True,
                text=True
            )
            
            assert SIGNAL_PATH.exists()
            signal = json.loads(SIGNAL_PATH.read_text())
            
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

    def test_multiple_passing_one_failing_scenario_results_in_pass_false_real(self):
        """Multiple scenarios with one failing aggregates to { pass: false }."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios_dir = Path(tmpdir) / "scenarios"
            scenarios_dir.mkdir()
            
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
                ['bash', '.orch/harness.sh', str(scenarios_dir), str(SIGNAL_PATH)],
                capture_output=True,
                text=True
            )
            
            # Signal should be pass:false even though 2 scenarios "passed"
            signal = json.loads(SIGNAL_PATH.read_text())
            assert signal == {"pass": False}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
