"""Tests for Clean Completion Signal (TC-04 from Section 4).

Scenario: All tasks in IMPLEMENTATION_PLAN.md marked done AND final scenario 
pass signal received -> /tmp/ralph-scenario-result.json contains { "done": true }
"""

import json
from pathlib import Path

import pytest

from src.signal import Signal


class TestCleanCompletionSignal:
    """Tests for clean completion signal (TC-04 from Section 4)."""

    def test_done_signal_written_when_all_tasks_complete(self, temp_signal_path: Path):
        """When all tasks complete, done signal is written to signal file."""
        # Simulate all tasks done scenario
        signal = Signal.done_signal()

        # Write to temp path
        original = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path
        try:
            signal.write()

            # Verify file contents
            content = json.loads(temp_signal_path.read_text())
            assert content == {"done": True}
        finally:
            Signal.SIGNAL_PATH = original

    def test_done_signal_contains_only_done_field(self, temp_signal_path: Path):
        """Done signal contains only 'done' field, no other keys."""
        signal = Signal.done_signal()
        result = signal.to_dict()

        # Must have only 'done' key
        assert "done" in result
        assert result["done"] is True

        # Must not have any other keys
        assert "pass" not in result
        assert "spinning" not in result
        assert "task" not in result
        assert "error" not in result
        assert "scenario" not in result

    def test_done_signal_read_roundtrip(self, temp_signal_path: Path):
        """Done signal survives write/read cycle."""
        signal = Signal.done_signal()

        original = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path
        try:
            signal.write()
            read_signal = Signal.read()
        finally:
            Signal.SIGNAL_PATH = original

        assert read_signal.done is True
        assert read_signal.pass_result is None
        assert read_signal.spinning is False


class TestDoneSignalIntegration:
    """Integration tests for done signal with Ralph loop."""

    def test_mark_done_writes_done_signal(self, temp_signal_path: Path):
        """Ralph.mark_done() writes done signal."""
        from src.ralph import Ralph

        original_signal_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            ralph = Ralph()
            ralph.plan = None  # No plan needed for done signal
            ralph.mark_done()

            # Check signal file
            content = json.loads(temp_signal_path.read_text())
            assert content == {"done": True}
        finally:
            Signal.SIGNAL_PATH = original_signal_path

    def test_done_signal_from_pass_signal_context(self, temp_signal_path: Path):
        """When harness sends pass signal but tasks are all done, should write done."""
        # Simulate: harness wrote pass signal, but Ralph checks and finds all tasks done
        original = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path
        try:
            # Write pass signal (simulating harness result)
            temp_signal_path.write_text('{"pass": true}')

            # Read it
            signal = Signal.read()
            assert signal.pass_result is True

            # Now if all tasks are done, we should convert to done signal
            all_tasks_done = True  # Simulating check
            if all_tasks_done and signal.pass_result is True:
                done_signal = Signal.done_signal()
                done_signal.write()

            # Verify done signal was written
            content = json.loads(temp_signal_path.read_text())
            assert content == {"done": True}
        finally:
            Signal.SIGNAL_PATH = original


class TestPlanMarkAllDone:
    """Tests for marking all tasks done in plan."""

    def test_mark_all_tasks_done(self):
        """Marking all tasks done updates plan file correctly."""
        from src.plan import ImplementationPlan

        # Create a plan with tasks
        plan = ImplementationPlan(project_name="Test Project")
        plan.add_task("Task 1", "Description 1")
        plan.add_task("Task 2", "Description 2")
        plan.add_task("Task 3", "Description 3")

        # Mark all tasks done
        for task in plan.tasks:
            task.status = "done"

        # Verify markdown output
        saved_content = plan.to_markdown()
        # Task.to_markdown uses [[x]] format for done tasks
        assert "[[x]]" in saved_content
        # Verify pending tasks are NOT marked done
        assert "[[ ]]" not in saved_content

    def test_get_current_task_returns_none_when_all_done(self):
        """get_current_task returns None when all tasks are done."""
        from src.plan import ImplementationPlan

        plan = ImplementationPlan(project_name="Test")
        plan.add_task("Task 1", "Desc 1")
        plan.add_task("Task 2", "Desc 2")

        # Mark all done
        for task in plan.tasks:
            task.status = "done"

        # Should return None (no pending tasks)
        current = plan.get_current_task()
        assert current is None


class TestDoneSignalLeakPrevention:
    """Tests ensuring done signal doesn't leak details."""

    def test_done_signal_json_has_no_extra_whitespace(self):
        """Done signal JSON is compact (no extra whitespace)."""
        signal = Signal.done_signal()
        json_str = json.dumps(signal.to_dict(), separators=(",", ":"))

        # Should be exactly {"done":true}
        assert json_str == '{"done":true}'
        assert " " not in json_str

    def test_done_signal_no_error_in_pass_context(self):
        """Done signal never contains error details."""
        signal = Signal.done_signal()
        result = signal.to_dict()
        json_str = json.dumps(result)

        forbidden = ["error", "failed", "fail", "assertion", "scenario", "message"]
        for word in forbidden:
            assert word not in json_str.lower() or word == "done", f"Leak: {word}"
