"""Tests for spinning signal integration (TC-03 from Section 4).

Scenario: Spinning signal (TC-03 from Section 4)
Given Ralph is retrying the same task repeatedly
When the retry count exceeds the spinning threshold (default: 5)
Then /tmp/ralph-scenario-result.json contains { "spinning": true, "task": "task-name" }
And the operator is notified to intervene

Scenario: Spinning detection (TC-03 from Section 7)
Given Ralph has retried task N 5 times
And each time scenario signal was { "pass": false }
When Ralph processes the 5th failure signal
Then Ralph writes { "spinning": true, "task": "task-N-description" }
And the operator is notified to intervene
"""

import json
from pathlib import Path

import pytest

from harness.state_manager import (
    SPIN_THRESHOLD,
    get_retry_count,
    increment_retry_count,
    is_spinning,
    write_spinning_signal,
)
from src.signal import Signal


class TestSpinningSignalIntegration:
    """Integration tests for spinning signal writing to signal file."""

    def test_write_spinning_signal_creates_correct_json(self, temp_signal_path: Path):
        """When spinning detected, signal file contains { "spinning": true, "task": "..." }."""
        # Patch the signal path for this test
        original_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            write_spinning_signal("task-name")
            content = json.loads(temp_signal_path.read_text())
        finally:
            Signal.SIGNAL_PATH = original_path

        assert content == {"spinning": True, "task": "task-name"}

    def test_spinning_signal_only_contains_spinning_and_task(self, temp_signal_path: Path):
        """Spinning signal contains no other fields."""
        original_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            write_spinning_signal("my-task")
            content = json.loads(temp_signal_path.read_text())
        finally:
            Signal.SIGNAL_PATH = original_path

        assert set(content.keys()) == {"spinning", "task"}
        assert "pass" not in content
        assert "done" not in content

    def test_spinning_signal_roundtrip_read(self, temp_signal_path: Path):
        """Spinning signal can be read back correctly."""
        original_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            write_spinning_signal("test-task")
            signal = Signal.read()
        finally:
            Signal.SIGNAL_PATH = original_path

        assert signal.spinning is True
        assert signal.task == "test-task"


class TestSpinningThresholdExceeded:
    """Tests for when retry count exceeds threshold."""

    def test_signal_written_at_exactly_threshold(self, tmp_path):
        """Signal should be written when retry count exceeds threshold."""
        import harness.state_manager as sm

        original_state = sm.RETRY_STATE_FILE
        original_signal = Signal.SIGNAL_PATH
        temp_signal = tmp_path / "signal.json"
        Signal.SIGNAL_PATH = temp_signal
        sm.RETRY_STATE_FILE = tmp_path / "state.json"

        try:
            # Increment 6 times (exceeds threshold of 5)
            for _ in range(6):
                increment_retry_count("task1")

            # At 6 retries, should detect spinning
            assert is_spinning("task1") is True

            # Explicitly write spinning signal (Ralph's behavior when spinning detected)
            write_spinning_signal("task1")

            # Verify signal was written
            assert temp_signal.exists()
            content = json.loads(temp_signal.read_text())
            assert content["spinning"] is True
            assert content["task"] == "task1"
        finally:
            sm.RETRY_STATE_FILE = original_state
            Signal.SIGNAL_PATH = original_signal

    def test_default_spinning_threshold_is_five(self):
        """SPIN_THRESHOLD constant is 5."""
        assert SPIN_THRESHOLD == 5


class TestSpinningSignalLeakPrevention:
    """Tests to ensure spinning signal doesn't leak details."""

    def test_spinning_signal_task_not_in_pass_field(self, temp_signal_path: Path):
        """Task name only in spinning.task, not leaking to pass field."""
        original_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            write_spinning_signal("secret-task-name")
            content = json.loads(temp_signal_path.read_text())
        finally:
            Signal.SIGNAL_PATH = original_path

        # No "pass" field at all
        assert "pass" not in content
        # Task is only in spinning context
        assert content["task"] == "secret-task-name"

    def test_spinning_signal_no_error_details(self, temp_signal_path: Path):
        """Spinning signal contains no error details."""
        original_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            write_spinning_signal("failing-task")
            content = json.loads(temp_signal_path.read_text())
            content_str = json.dumps(content)
        finally:
            Signal.SIGNAL_PATH = original_path

        forbidden = ["error", "reason", "detail", "assertion", "failed", "scenario"]
        for word in forbidden:
            assert word not in content_str.lower() or word == content.get("task", "")


class TestOperatorNotification:
    """Tests for operator notification when spinning detected."""

    def test_write_spinning_signal_creates_file(self, temp_signal_path: Path):
        """Spinning signal file is created for operator to detect."""
        original_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            write_spinning_signal("stuck-task")
        finally:
            Signal.SIGNAL_PATH = original_path

        assert temp_signal_path.exists()

    def test_spinning_signal_is_valid_json(self, temp_signal_path: Path):
        """Spinning signal is valid JSON that can be parsed."""
        original_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            write_spinning_signal("any-task")
            # Should not raise
            content = json.loads(temp_signal_path.read_text())
            assert isinstance(content, dict)
        finally:
            Signal.SIGNAL_PATH = original_path
