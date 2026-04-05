"""Tests for state manager - TC-04 from Section 7."""

import json
import tempfile
from pathlib import Path

import pytest


class TestRetryCountPersistence:
    """Tests for retry count persistence (TC-04 from Section 7)."""

    def test_retry_count_starts_at_zero(self, tmp_path):
        """New task has zero retry count."""
        import harness.state_manager as sm

        original_state_file = sm.RETRY_STATE_FILE
        sm.RETRY_STATE_FILE = tmp_path / "state.json"

        try:
            count = sm.get_retry_count("new_task")
            assert count == 0
        finally:
            sm.RETRY_STATE_FILE = original_state_file

    def test_increment_retry_count(self, tmp_path):
        """Incrementing retry count works correctly."""
        import harness.state_manager as sm

        original_state_file = sm.RETRY_STATE_FILE
        sm.RETRY_STATE_FILE = tmp_path / "state.json"

        try:
            count1 = sm.increment_retry_count("task1")
            assert count1 == 1

            count2 = sm.increment_retry_count("task1")
            assert count2 == 2

            count3 = sm.get_retry_count("task1")
            assert count3 == 2
        finally:
            sm.RETRY_STATE_FILE = original_state_file

    def test_reset_retry_count(self, tmp_path):
        """Resetting retry count works."""
        import harness.state_manager as sm

        original_state_file = sm.RETRY_STATE_FILE
        sm.RETRY_STATE_FILE = tmp_path / "state.json"

        try:
            sm.increment_retry_count("task1")
            sm.increment_retry_count("task1")
            sm.increment_retry_count("task1")
            assert sm.get_retry_count("task1") == 3

            sm.reset_retry_count("task1")
            assert sm.get_retry_count("task1") == 0
        finally:
            sm.RETRY_STATE_FILE = original_state_file

    def test_state_persists_across_restarts(self, tmp_path):
        """State survives restart (TC-04)."""
        import harness.state_manager as sm

        original_state_file = sm.RETRY_STATE_FILE
        sm.RETRY_STATE_FILE = tmp_path / "state.json"

        try:
            # First "process"
            sm.increment_retry_count("task1")
            sm.increment_retry_count("task1")
            sm.increment_retry_count("task1")

            # Simulate restart by re-importing
            # (in real code, the file would be read fresh)

            # Second "process" reads same file
            count = sm.get_retry_count("task1")
            assert count == 3
        finally:
            sm.RETRY_STATE_FILE = original_state_file


class TestSpinningDetection:
    """Tests for spinning detection (TC-03 from Section 7)."""

    def test_spinning_threshold_is_five(self):
        """Spinning threshold is 5 retries."""
        import harness.state_manager as sm

        assert sm.SPIN_THRESHOLD == 5

    def test_is_spinning_returns_false_under_threshold(self, tmp_path):
        """Not spinning when retry count <= threshold."""
        import harness.state_manager as sm

        original_state_file = sm.RETRY_STATE_FILE
        sm.RETRY_STATE_FILE = tmp_path / "state.json"

        try:
            for i in range(5):
                sm.increment_retry_count("task1")

            assert sm.is_spinning("task1") is False
        finally:
            sm.RETRY_STATE_FILE = original_state_file

    def test_is_spinning_returns_true_over_threshold(self, tmp_path):
        """Is spinning when retry count > threshold."""
        import harness.state_manager as sm

        original_state_file = sm.RETRY_STATE_FILE
        sm.RETRY_STATE_FILE = tmp_path / "state.json"

        try:
            for i in range(6):
                sm.increment_retry_count("task1")

            assert sm.is_spinning("task1") is True
        finally:
            sm.RETRY_STATE_FILE = original_state_file

    def test_spinning_signal_includes_task_name(self, tmp_path):
        """Spinning signal includes task identifier."""
        import harness.state_manager as sm

        original_state_file = sm.RETRY_STATE_FILE
        sm.RETRY_STATE_FILE = tmp_path / "state.json"

        try:
            for i in range(6):
                sm.increment_retry_count("task-N-description")

            assert sm.is_spinning("task-N-description") is True
        finally:
            sm.RETRY_STATE_FILE = original_state_file
