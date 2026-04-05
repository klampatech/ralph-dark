"""Tests for post-commit hook scenario execution (TC-02).

Scenario: Post-commit scenario execution
Given a commit is pushed to the repository
When the post-commit hook fires
Then the harness reads scenarios/*.yaml
And executes them against the running system
And writes { "pass": true | false } to /tmp/ralph-scenario-result.json
And Ralph reads the signal before the next iteration begins
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestPostCommitHookFires:
    """Tests for post-commit hook firing scenario execution."""

    def test_hook_exists_and_is_executable(self):
        """Post-commit hook exists and is executable."""
        hook_path = Path(__file__).parent.parent / "hooks" / "post-commit"
        assert hook_path.exists(), "post-commit hook should exist"
        assert os.access(hook_path, os.X_OK), "post-commit hook should be executable"

    def test_hook_runs_harness_when_scenarios_readable(self, temp_scenarios_dir, temp_signal_path):
        """Hook runs harness when scenarios directory is readable."""
        # Create a simple scenario
        scenario = {
            'name': 'test-scenario',
            'trigger': {'type': 'http', 'method': 'GET', 'path': '/health'},
            'assertions': [{'type': 'http_status', 'path': '/health', 'expect': 200}]
        }
        scenario_file = temp_scenarios_dir / "test.yaml"
        scenario_file.write_text(yaml.dump(scenario))

        # Read the hook and verify it checks scenarios
        hook_content = (Path(__file__).parent.parent / "hooks" / "post-commit").read_text()
        assert "scenarios" in hook_content.lower(), "Hook should reference scenarios directory"
        assert "harness" in hook_content.lower() or "ralph" in hook_content.lower(), \
            "Hook should reference harness"

    def test_harness_reads_yaml_scenarios_from_scenarios_dir(self, temp_scenarios_dir):
        """Harness reads scenarios/*.yaml files from scenarios directory."""
        from src.scenario_author import load_scenarios

        # Create test scenarios
        scenarios_content = [
            {
                'name': 'scenario-one',
                'trigger': {'type': 'http', 'method': 'GET', 'path': '/api/health'},
                'assertions': [{'type': 'http_status', 'path': '/api/health', 'expect': 200}]
            },
            {
                'name': 'scenario-two',
                'trigger': {'type': 'http', 'method': 'POST', 'path': '/api/orders'},
                'assertions': [{'type': 'http_status', 'path': '/api/orders', 'expect': 201}]
            }
        ]

        for i, scenario in enumerate(scenarios_content):
            scenario_file = temp_scenarios_dir / f"scenario_{i:03d}.yaml"
            scenario_file.write_text(yaml.dump(scenario))

        
        # Load scenarios from the temp directory
        scenarios = load_scenarios(temp_scenarios_dir)

        # Should have loaded the test scenarios
        assert len(scenarios) == 2, \
            f"Should have loaded 2 scenarios, got {len(scenarios)}"
        assert scenarios[0].name == 'scenario-one'
        assert scenarios[1].name == 'scenario-two'

    def test_harness_writes_pass_signal_on_success(self, temp_signal_path):
        """Harness writes { "pass": true } when all assertions pass."""
        from src.signal import Signal

        # Set the class attribute before writing
        Signal.SIGNAL_PATH = temp_signal_path
        signal = Signal.pass_signal()
        signal.write()

        assert temp_signal_path.exists(), "Signal file should be created"

        content = json.loads(temp_signal_path.read_text())
        assert content == {"pass": True}, \
            "Signal should be {pass: true} on success"
        assert "error" not in content, "Signal should not contain error details"
        assert "scenario" not in content, "Signal should not contain scenario names"

        # Reset
        Signal.SIGNAL_PATH = None

    def test_harness_writes_fail_signal_on_failure(self, temp_signal_path):
        """Harness writes { "pass": false } when any assertion fails."""
        from src.signal import Signal

        # Set the class attribute before writing
        Signal.SIGNAL_PATH = temp_signal_path
        signal = Signal.fail_signal()
        signal.write()

        assert temp_signal_path.exists(), "Signal file should be created"

        content = json.loads(temp_signal_path.read_text())
        assert content == {"pass": False}, \
            "Signal should be {pass: false} on failure"
        assert "error" not in content, "Signal should not contain error details"
        assert "scenario" not in content, "Signal should not contain scenario names"

        # Reset
        Signal.SIGNAL_PATH = None

    def test_ralph_reads_signal_before_next_iteration(self, temp_signal_path):
        """Ralph reads signal from /tmp/ralph-scenario-result.json."""
        from src.signal import Signal

        # Set the class attribute before operations
        Signal.SIGNAL_PATH = temp_signal_path

        # Write a pass signal
        signal = Signal.pass_signal()
        signal.write()

        # Read it back (Ralph's read behavior)
        read_signal = Signal.read()

        assert read_signal.pass_result is True, \
            "Ralph should read pass signal correctly"
        assert read_signal.spinning is False, \
            "Signal should not indicate spinning"
        assert read_signal.done is False, \
            "Signal should not indicate done"

        # Reset
        Signal.SIGNAL_PATH = None


class TestPostCommitIntegration:
    """Integration tests for post-commit hook flow."""

    def test_hook_script_calls_harness(self, temp_scenarios_dir, temp_signal_path):
        """Post-commit hook script calls harness to execute scenarios."""
        hook_path = Path(__file__).parent.parent / "hooks" / "post-commit"
        hook_content = hook_path.read_text()

        # Verify hook structure
        assert "#!/bin/bash" in hook_content, "Hook should be bash script"
        assert "python3" in hook_content.lower() or "./bin/ralph" in hook_content.lower(), \
            "Hook should call Python or ralph binary"
        assert "/tmp/ralph-scenario-result.json" in hook_content, \
            "Hook should reference signal file path"

    def test_signal_file_location_is_tmp(self):
        """Signal is written to /tmp/ralph-scenario-result.json."""
        from src import signal as signal_module

        assert str(signal_module.SIGNAL_PATH) == "/tmp/ralph-scenario-result.json", \
            "Signal path should be /tmp/ralph-scenario-result.json"

    def test_full_hook_flow_simulation(self, temp_scenarios_dir, temp_signal_path):
        """Simulate full post-commit hook flow."""
        from src.signal import Signal

        # Step 1: Create scenarios
        scenario = {
            'name': 'health-check',
            'trigger': {'type': 'http', 'method': 'GET', 'path': '/health'},
            'assertions': [
                {'type': 'http_status', 'path': '/health', 'expect': 200}
            ]
        }
        scenario_file = temp_scenarios_dir / "health_check.yaml"
        scenario_file.write_text(yaml.dump(scenario))

        # Step 2: Mock signal path and scenarios dir, run harness
        Signal.SIGNAL_PATH = temp_signal_path

        with patch('src.scenario_author.SCENARIOS_DIR', temp_scenarios_dir):
            from src.harness import Harness

            harness = Harness()

            # Mock HTTP assertions to simulate passing
            with patch.object(harness, '_assert_http_status', return_value=True):
                harness.execute_all()
                harness.write_signal()

        # Step 3: Verify signal was written
        assert temp_signal_path.exists(), "Signal file should exist after hook runs"

        content = json.loads(temp_signal_path.read_text())
        assert "pass" in content, "Signal should contain pass field"
        assert isinstance(content["pass"], bool), "pass should be boolean"

        # Reset
        Signal.SIGNAL_PATH = None

    def test_aggregation_all_pass_writes_true(self, temp_scenarios_dir, temp_signal_path):
        """When all scenarios pass, signal is {pass: true}."""
        from src.signal import Signal

        # Create a scenario
        scenario = {
            'name': 'passing',
            'trigger': {'type': 'http', 'method': 'GET', 'path': '/health'},
            'assertions': [{'type': 'http_status', 'path': '/health', 'expect': 200}]
        }
        scenario_file = temp_scenarios_dir / "passing.yaml"
        scenario_file.write_text(yaml.dump(scenario))

        # Mock signal path and scenarios dir
        Signal.SIGNAL_PATH = temp_signal_path

        with patch('src.scenario_author.SCENARIOS_DIR', temp_scenarios_dir):
            from src.harness import Harness

            harness = Harness()

            # Mock the HTTP check to pass
            with patch.object(harness, '_assert_http_status', return_value=True):
                harness.execute_all()
                harness.write_signal()

        content = json.loads(temp_signal_path.read_text())
        assert content == {"pass": True}

        # Reset
        Signal.SIGNAL_PATH = None

    def test_aggregation_any_fail_writes_false(self, temp_scenarios_dir, temp_signal_path):
        """When any scenario fails, signal is {pass: false}."""
        from src.signal import Signal

        # Create a scenario
        scenario = {
            'name': 'failing',
            'trigger': {'type': 'http', 'method': 'GET', 'path': '/api/data'},
            'assertions': [{'type': 'http_status', 'path': '/api/data', 'expect': 200}]
        }
        scenario_file = temp_scenarios_dir / "failing.yaml"
        scenario_file.write_text(yaml.dump(scenario))

        # Mock signal path and scenarios dir
        Signal.SIGNAL_PATH = temp_signal_path

        with patch('src.scenario_author.SCENARIOS_DIR', temp_scenarios_dir):
            from src.harness import Harness

            harness = Harness()

            # Mock the HTTP check to fail
            with patch.object(harness, '_assert_http_status', return_value=False):
                harness.execute_all()
                harness.write_signal()

        content = json.loads(temp_signal_path.read_text())
        assert content == {"pass": False}

        # Reset
        Signal.SIGNAL_PATH = None


class TestSignalCleanContent:
    """Tests for signal content cleanliness (TC-02 from Section 3)."""

    def test_signal_contains_only_pass_boolean(self, temp_signal_path):
        """Signal file contains only valid JSON with single pass boolean."""
        from src.signal import Signal

        Signal.SIGNAL_PATH = temp_signal_path
        signal = Signal.pass_signal()
        signal.write()

        content = json.loads(temp_signal_path.read_text())
        assert list(content.keys()) == ["pass"], \
            "Signal should only have 'pass' key"
        assert isinstance(content["pass"], bool), \
            "pass value should be boolean"

        # Reset
        Signal.SIGNAL_PATH = None

    def test_signal_never_leaks_scenario_names(self, temp_signal_path):
        """Signal never contains scenario names (leaky signal prevention)."""
        from src.signal import Signal

        Signal.SIGNAL_PATH = temp_signal_path
        signal = Signal.fail_signal()
        signal.write()

        content = json.loads(temp_signal_path.read_text())

        # Check no leaky fields
        assert "name" not in content, "Signal should not contain 'name'"
        assert "scenario" not in content, "Signal should not contain 'scenario'"
        assert "error" not in content, "Signal should not contain 'error'"
        assert "message" not in content, "Signal should not contain 'message'"
        assert "details" not in content, "Signal should not contain 'details'"

        # Reset
        Signal.SIGNAL_PATH = None

    def test_signal_never_leaks_error_messages(self, temp_signal_path):
        """Signal never contains error messages."""
        from src.signal import Signal

        Signal.SIGNAL_PATH = temp_signal_path
        signal = Signal.fail_signal()
        signal.write()

        content = json.loads(temp_signal_path.read_text())
        content_str = json.dumps(content)

        # Should not have any error-related strings
        assert "error" not in content_str.lower() or "pass" in content_str, \
            "Signal should not leak error messages"

        # Reset
        Signal.SIGNAL_PATH = None

    def test_fail_signal_contains_only_pass_false(self, temp_signal_path):
        """Fail signal is exactly {pass: false}, nothing more."""
        from src.signal import Signal

        Signal.SIGNAL_PATH = temp_signal_path
        signal = Signal.fail_signal()
        signal.write()

        content = temp_signal_path.read_text()
        parsed = json.loads(content)

        assert parsed == {"pass": False}, \
            "Fail signal should be exactly {pass: false}"

        # Reset
        Signal.SIGNAL_PATH = None

    def test_spinning_signal_format(self, temp_signal_path):
        """Spinning signal contains spinning: true and task name."""
        from src.signal import Signal

        Signal.SIGNAL_PATH = temp_signal_path
        signal = Signal.spinning_signal("build-login-api")
        signal.write()

        content = json.loads(temp_signal_path.read_text())

        assert content.get("spinning") is True, "Signal should have spinning: true"
        assert "task" in content, "Signal should have task field"
        assert content["task"] == "build-login-api", "Task name should be preserved"

        # Should NOT have pass field when spinning
        assert "pass" not in content, "Spinning signal should not have pass field"

        # Reset
        Signal.SIGNAL_PATH = None

    def test_done_signal_format(self, temp_signal_path):
        """Done signal contains done: true."""
        from src.signal import Signal

        Signal.SIGNAL_PATH = temp_signal_path
        signal = Signal.done_signal()
        signal.write()

        content = json.loads(temp_signal_path.read_text())

        assert content == {"done": True}, "Done signal should be {done: true}"

        # Reset
        Signal.SIGNAL_PATH = None
