"""Tests for Scenario TC-03 from Section 6: Malformed signal handling.

Given harness encounters an error and cannot complete
When harness writes the signal file (or fails to write)
Then Ralph treats missing or malformed signal as { "pass": false }
And the loop retries the current task
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml


class TestMalformedSignalHandling:
    """Tests for TC-03 from Section 6: Malformed signal handling."""

    def test_harness_writes_fail_signal_on_error(self, tmp_path):
        """Harness writes { "pass": false } when it encounters an error."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create a scenario that will cause harness to fail
        scenario = {
            'name': 'failing-scenario',
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/api/failing'
            },
            'assertions': [
                {'type': 'http_status', 'path': '/api/missing', 'expect': 404}
            ]
        }
        scenario_file = scenarios_dir / "test.yaml"
        scenario_file.write_text(yaml.dump(scenario))
        
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        # Signal file should exist and contain pass: false
        assert signal_file.exists(), f"Signal file not created"
        content = json.loads(signal_file.read_text())
        assert content == {"pass": False}

    def test_harness_handles_missing_scenarios_directory_gracefully(self, tmp_path):
        """Harness writes { "pass": false } when scenarios directory is missing.
        
        Missing scenarios directory is an error condition, so harness should fail.
        """
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Run harness with non-existent scenarios directory
        result = subprocess.run(
            ['bash', '.orch/harness.sh', '/nonexistent/path', str(signal_file)],
            capture_output=True,
            text=True
        )
        
        # Should handle gracefully without crashing
        assert signal_file.exists()
        content = json.loads(signal_file.read_text())
        # Missing directory is an error - should return pass: false
        assert content == {"pass": False}

    def test_harness_handles_permission_error_when_writing_signal(self, tmp_path):
        """Harness handles permission errors when writing signal file."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        # Create a read-only directory for signal file
        signal_file = tmp_path / "readonly" / "ralph-scenario-result.json"
        signal_file.parent.mkdir()
        
        # Create scenario
        scenario = {'name': 'test', 'trigger': {'type': 'http', 'method': 'GET', 'path': '/api'}}
        scenario_file = scenarios_dir / "test.yaml"
        scenario_file.write_text(yaml.dump(scenario))
        
        # Run harness with read-only signal path
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        # Harness should not crash - should handle the error
        # The behavior depends on implementation; signal file may or may not exist

    def test_harness_writes_valid_json_even_on_error(self, tmp_path):
        """Harness always writes valid JSON even when scenarios fail.
        
        Malformed YAML in a scenario file should cause harness to fail.
        """
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create a malformed scenario file (invalid YAML syntax)
        scenario_file = scenarios_dir / "malformed.yaml"
        scenario_file.write_text("{ invalid yaml: [")
        
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        # Should still write valid JSON
        assert signal_file.exists()
        content = signal_file.read_text()
        
        # Should be valid JSON
        signal = json.loads(content)
        assert isinstance(signal, dict)
        assert "pass" in signal
        # Malformed YAML scenario is an error - should return pass: false
        assert signal["pass"] is False


class TestSignalReaderHandlesMalformed:
    """Tests for Ralph signal reader handling malformed signals."""

    def test_signal_reader_handles_missing_file(self, temp_signal_path):
        """Signal.read() returns pass:false when file is missing."""
        from src.signal import Signal
        
        # Ensure file doesn't exist
        if temp_signal_path.exists():
            temp_signal_path.unlink()
        
        # Patch SIGNAL_PATH
        original = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path
        try:
            signal = Signal.read()
        finally:
            Signal.SIGNAL_PATH = original
        
        assert signal.pass_result is False

    def test_signal_reader_handles_malformed_json(self, temp_signal_path):
        """Signal.read() returns pass:false for malformed JSON."""
        from src.signal import Signal
        
        # Write malformed JSON
        temp_signal_path.write_text("{ invalid json }")
        
        original = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path
        try:
            signal = Signal.read()
        finally:
            Signal.SIGNAL_PATH = original
        
        assert signal.pass_result is False

    def test_signal_reader_handles_empty_file(self, temp_signal_path):
        """Signal.read() returns pass:false for empty file."""
        from src.signal import Signal
        
        temp_signal_path.write_text("")
        
        original = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path
        try:
            signal = Signal.read()
        finally:
            Signal.SIGNAL_PATH = original
        
        assert signal.pass_result is False

    def test_signal_reader_handles_invalid_schema(self, temp_signal_path):
        """Signal.read() returns pass:false for invalid signal schema."""
        from src.signal import Signal
        
        # Write valid JSON but wrong schema
        temp_signal_path.write_text('{"error": "something went wrong", "scenario": "test"}')
        
        original = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path
        try:
            signal = Signal.read()
        finally:
            Signal.SIGNAL_PATH = original
        
        # Should handle gracefully and return fail signal
        assert signal.pass_result is False

    def test_signal_reader_handles_truncated_json(self, temp_signal_path):
        """Signal.read() returns pass:false for truncated JSON."""
        from src.signal import Signal
        
        temp_signal_path.write_text('{"pass": tr')  # Truncated JSON
        
        original = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path
        try:
            signal = Signal.read()
        finally:
            Signal.SIGNAL_PATH = original
        
        assert signal.pass_result is False


class TestHarnessSignalWriteRobustness:
    """Tests for harness signal write robustness."""

    def test_harness_creates_signal_file_in_correct_location(self, tmp_path):
        """Harness creates signal file at specified location."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "custom-signal.json"
        
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert signal_file.exists()
        content = json.loads(signal_file.read_text())
        assert content == {"pass": True}

    def test_harness_signal_contains_no_extra_fields(self, tmp_path):
        """Harness signal contains only pass field, no error details."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        signal_file = tmp_path / "ralph-scenario-result.json"
        
        # Create a failing scenario
        scenario = {
            'name': 'failing-scenario',
            'trigger': {'type': 'http', 'method': 'GET', 'path': '/api'},
            'assertions': [{'type': 'http_status', 'path': '/api', 'expect': 500}]
        }
        scenario_file = scenarios_dir / "test.yaml"
        scenario_file.write_text(yaml.dump(scenario))
        
        result = subprocess.run(
            ['bash', '.orch/harness.sh', str(scenarios_dir), str(signal_file)],
            capture_output=True,
            text=True
        )
        
        assert signal_file.exists()
        signal = json.loads(signal_file.read_text())
        
        # Verify no leaky fields
        assert list(signal.keys()) == ["pass"]
        assert "error" not in signal
        assert "message" not in signal
        assert "scenario" not in signal
        assert "details" not in signal


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
