"""Tests for signal.py - signal handling and file I/O."""

import json
from pathlib import Path

import pytest

from src.signal import SIGNAL_PATH, Signal


class TestSignalPassCases:
    """Tests for clean pass signal."""

    def test_pass_signal_creates_correct_dict(self):
        """Clean pass signal: { "pass": true }."""
        signal = Signal.pass_signal()
        result = signal.to_dict()
        assert result == {"pass": True}
        assert "spinning" not in result
        assert "done" not in result
        assert "task" not in result

    def test_pass_signal_from_dict(self):
        """Signal.from_dict handles pass:true correctly."""
        signal = Signal.from_dict({"pass": True})
        assert signal.pass_result is True
        assert signal.spinning is False
        assert signal.done is False

    def test_pass_signal_roundtrip(self, temp_signal_path: Path):
        """Pass signal survives write/read cycle without leaking details."""
        import src.signal as signal_module
        signal = Signal.pass_signal()
        original = signal_module.SIGNAL_PATH
        signal_module.SIGNAL_PATH = temp_signal_path
        try:
            signal.write()
            content = json.loads(temp_signal_path.read_text())
        finally:
            signal_module.SIGNAL_PATH = original
        assert content == {"pass": True}
        assert "scenario" not in content
        assert "error" not in content
        assert "task" not in content


class TestSignalFailCases:
    """Tests for clean fail signal."""

    def test_fail_signal_creates_correct_dict(self):
        """Clean fail signal: { "pass": false }."""
        signal = Signal.fail_signal()
        result = signal.to_dict()
        assert result == {"pass": False}
        assert "spinning" not in result
        assert "done" not in result
        assert "task" not in result

    def test_fail_signal_from_dict(self):
        """Signal.from_dict handles pass:false correctly."""
        signal = Signal.from_dict({"pass": False})
        assert signal.pass_result is False
        assert signal.spinning is False
        assert signal.done is False

    def test_fail_signal_roundtrip(self, temp_signal_path: Path):
        """Fail signal survives write/read cycle without leaking details."""
        import src.signal as signal_module
        signal = Signal.fail_signal()
        original = signal_module.SIGNAL_PATH
        signal_module.SIGNAL_PATH = temp_signal_path
        try:
            signal.write()
            content = json.loads(temp_signal_path.read_text())
        finally:
            signal_module.SIGNAL_PATH = original
        assert content == {"pass": False}
        assert "scenario" not in content
        assert "error" not in content
        assert "task" not in content


class TestSignalSpinningCases:
    """Tests for spinning signal."""

    def test_spinning_signal_creates_correct_dict(self):
        """Spinning signal: { "spinning": true, "task": "..." }."""
        signal = Signal.spinning_signal("test-task-name")
        result = signal.to_dict()
        assert result == {"spinning": True, "task": "test-task-name"}

    def test_spinning_signal_from_dict(self):
        """Signal.from_dict handles spinning:true correctly."""
        signal = Signal.from_dict({"spinning": True, "task": "my-task"})
        assert signal.spinning is True
        assert signal.task == "my-task"
        assert signal.pass_result is None

    def test_spinning_signal_does_not_leak_task_name_in_pass_field(self):
        """Spinning signal task name only appears in spinning field."""
        signal = Signal.spinning_signal("secret-task")
        result = signal.to_dict()
        assert "pass" not in result
        assert result["task"] == "secret-task"
        # Verify the task is NOT in pass field
        assert result.get("pass", None) is None

    def test_spinning_signal_task_is_masked_in_output(self):
        """Spinning signal task field name is masked in output."""
        signal = Signal.spinning_signal("task-N-description")
        result = signal.to_dict()
        # Task appears only in dedicated field, not scattered
        assert result["task"] == "task-N-description"
        # No scenario or error details
        assert "scenario" not in result
        assert "error" not in result


class TestSignalDoneCases:
    """Tests for done signal."""

    def test_done_signal_creates_correct_dict(self):
        """Done signal: { "done": true }."""
        signal = Signal.done_signal()
        result = signal.to_dict()
        assert result == {"done": True}
        assert "pass" not in result
        assert "spinning" not in result

    def test_done_signal_from_dict(self):
        """Signal.from_dict handles done:true correctly."""
        signal = Signal.from_dict({"done": True})
        assert signal.done is True
        assert signal.spinning is False
        assert signal.pass_result is None


class TestSignalLeakPrevention:
    """Tests for signal content leak prevention."""

    def test_no_scenario_names_in_pass_signal(self):
        """Pass signal never contains scenario names."""
        signal = Signal.pass_signal()
        result = json.dumps(signal.to_dict())
        assert "scenario" not in result.lower() or "scenario" not in signal.to_dict()

    def test_no_error_details_in_fail_signal(self):
        """Fail signal never contains error messages or details."""
        signal = Signal.fail_signal()
        result = json.dumps(signal.to_dict())
        result_dict = signal.to_dict()
        # Must not have error, message, detail, reason keys
        forbidden_keys = ["error", "message", "detail", "reason", "scenario"]
        for key in forbidden_keys:
            assert key not in result_dict, f"Leak detected: {key} found in signal"

    def test_no_failure_details_in_any_signal(self):
        """No signal type contains failure details."""
        signal_types = [
            Signal.pass_signal(),
            Signal.fail_signal(),
            Signal.spinning_signal("task"),
            Signal.done_signal(),
        ]
        for signal in signal_types:
            result_dict = signal.to_dict()
            content = json.dumps(result_dict)
            # Verify no scenario identifiers or error content
            assert not any(
                word in content.lower()
                for word in ["failed", "error", "assertion", "scenario"]
                if word not in ["pass"]  # pass is allowed in pass/fail context
            ), f"Leak detected in {signal_types.index(signal)} signal"


class TestSignalRead:
    """Tests for reading signals from file."""

    def test_read_missing_file_returns_fail_signal(self):
        """Missing signal file is treated as fail."""
        import src.signal as signal_module
        original = signal_module.SIGNAL_PATH
        signal_module.SIGNAL_PATH = Path("/tmp/nonexistent_signal_file.json")
        try:
            signal = Signal.read()
        finally:
            signal_module.SIGNAL_PATH = original
        assert signal.pass_result is False

    def test_read_malformed_json_returns_fail_signal(self, temp_signal_path: Path):
        """Malformed JSON is treated as fail."""
        import src.signal as signal_module
        temp_signal_path.write_text("{ invalid json }")
        original = signal_module.SIGNAL_PATH
        signal_module.SIGNAL_PATH = temp_signal_path
        try:
            signal = Signal.read()
        finally:
            signal_module.SIGNAL_PATH = original
        assert signal.pass_result is False

    def test_read_valid_pass_signal(self, temp_signal_path: Path):
        """Reading valid pass signal works correctly."""
        import src.signal as signal_module
        temp_signal_path.write_text('{"pass": true}')
        original = signal_module.SIGNAL_PATH
        signal_module.SIGNAL_PATH = temp_signal_path
        try:
            signal = Signal.read()
        finally:
            signal_module.SIGNAL_PATH = original
        assert signal.pass_result is True

    def test_read_valid_spinning_signal(self, temp_signal_path: Path):
        """Reading spinning signal works correctly."""
        import src.signal as signal_module
        temp_signal_path.write_text('{"spinning": true, "task": "my-task"}')
        original = signal_module.SIGNAL_PATH
        signal_module.SIGNAL_PATH = temp_signal_path
        try:
            signal = Signal.read()
        finally:
            signal_module.SIGNAL_PATH = original
        assert signal.spinning is True
        assert signal.task == "my-task"


class TestSignalDefaults:
    """Tests for signal default behavior."""

    def test_empty_to_dict_returns_fail(self):
        """Signal with no fields set defaults to fail."""
        signal = Signal()
        result = signal.to_dict()
        assert result == {"pass": False}

    def test_signal_attributes_default_to_none_or_false(self):
        """Signal dataclass has correct defaults."""
        signal = Signal()
        assert signal.pass_result is None
        assert signal.spinning is False
        assert signal.task is None
        assert signal.done is False
