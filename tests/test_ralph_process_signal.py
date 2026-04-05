"""Tests for Ralph process_signal functionality.

These tests verify that:
1. Ralph.load_plan() sets current_task correctly
2. process_signal() handles pass/fail signals correctly
3. Spinning detection works after 5 failures
4. Task advancement works on pass signals
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.ralph import Ralph
from src.signal import Signal
from src.plan import ImplementationPlan


class TestRalphLoadPlanSetsCurrentTask:
    """Tests to verify load_plan() sets current_task correctly."""

    def test_load_plan_sets_current_task(self, tmp_path):
        """After load_plan(), Ralph.current_task should be set."""
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("""# Implementation Plan: Test

## Tasks

- [ ] **First Task** (T001)
  Description for first task
- [ ] **Second Task** (T002)
  Description for second task

---
*Auto-generated*
""")

        with patch("src.plan.IMPLEMENTATION_PLAN", plan_file):
            ralph = Ralph(project_path=str(tmp_path))
            ralph.load_plan()

            # current_task should be set after load_plan()
            assert ralph.current_task is not None
            assert ralph.current_task.id == "T001"
            assert ralph.current_task.title == "First Task"

    def test_load_plan_skips_done_tasks(self, tmp_path):
        """load_plan() should skip already-done tasks."""
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("""# Implementation Plan: Test

## Tasks

- [x] **Completed Task** (T001)
  Already done
- [ ] **Pending Task** (T002)
  This should be current

---
*Auto-generated*
""")

        with patch("src.plan.IMPLEMENTATION_PLAN", plan_file):
            ralph = Ralph(project_path=str(tmp_path))
            ralph.load_plan()

            # Should skip T001 (done) and set T002 as current
            assert ralph.current_task is not None
            assert ralph.current_task.id == "T002"


class TestProcessSignalFailsTask:
    """Tests for process_signal() handling fail signals."""

    def test_fail_signal_increments_plan_retry_count(self, tmp_path, temp_signal_path):
        """Fail signal should increment the plan's retry count for the task."""
        import time
        unique_suffix = int(time.time() * 1000) % 100000
        task_id = f"T_TEST_{unique_suffix}"
        
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(f"""# Implementation Plan: Test

## Tasks

- [ ] **Failing Task** ({task_id})
  This task will fail

---
*Auto-generated*
""")
        
        original_signal_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            with patch("src.plan.IMPLEMENTATION_PLAN", plan_file):
                ralph = Ralph(project_path=str(tmp_path))
                ralph.load_plan()
                
                # Get actual task ID from loaded plan
                actual_task_id = ralph.current_task.id

                # Initial retry count should be 0
                assert ralph.plan.tasks[0].retry_count == 0

                # Write fail signal
                temp_signal_path.write_text('{"pass": false}')
                ralph.load_signal()
                ralph.process_signal()

                # After processing fail, plan's retry count should be 1
                assert ralph.plan.tasks[0].retry_count == 1
        finally:
            Signal.SIGNAL_PATH = original_signal_path

    def test_process_signal_writes_spinning_after_five_failures(
        self, tmp_path, temp_signal_path
    ):
        """After 5 consecutive failures, spinning signal should be written."""
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("""# Implementation Plan: Test

## Tasks

- [ ] **Spinning Task** (T001)
  This task keeps failing

---
*Auto-generated*
""")

        original_signal_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            with patch("src.plan.IMPLEMENTATION_PLAN", plan_file):
                ralph = Ralph(project_path=str(tmp_path))
                ralph.load_plan()

                # Simulate 5 failures
                for i in range(5):
                    temp_signal_path.write_text('{"pass": false}')
                    ralph.load_signal()
                    ralph.process_signal()

                # After 5th failure, spinning signal should be written
                assert temp_signal_path.exists()
                content = json.loads(temp_signal_path.read_text())
                assert content.get("spinning") is True
                assert "task" in content
                assert "Spinning Task" in content["task"]
        finally:
            Signal.SIGNAL_PATH = original_signal_path


class TestProcessSignalPassTask:
    """Tests for process_signal() handling pass signals."""

    def test_pass_signal_marks_task_done(self, tmp_path, temp_signal_path):
        """Pass signal should mark current task as done."""
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("""# Implementation Plan: Test

## Tasks

- [ ] **Passing Task** (T001)
  This task will pass
- [ ] **Next Task** (T002)
  Next task after T001

---
*Auto-generated*
""")

        original_signal_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            with patch("src.plan.IMPLEMENTATION_PLAN", plan_file):
                ralph = Ralph(project_path=str(tmp_path))
                ralph.load_plan()

                # Verify starting at T001
                assert ralph.current_task.id == "T001"
                assert ralph.current_task.status == "pending"

                # Write pass signal
                temp_signal_path.write_text('{"pass": true}')
                ralph.load_signal()
                ralph.process_signal()

                # T001 should be marked done
                t001 = next(t for t in ralph.plan.tasks if t.id == "T001")
                assert t001.status == "done"

                # T002 should be current
                assert ralph.current_task.id == "T002"
        finally:
            Signal.SIGNAL_PATH = original_signal_path


class TestSpinningThreshold:
    """Tests to verify spinning threshold is correctly set to 5."""

    def test_spinning_threshold_is_five(self):
        """Ralph.SPINNING_THRESHOLD should be 5."""
        ralph = Ralph()
        assert ralph.SPINNING_THRESHOLD == 5

    def test_spinning_at_four_failures_is_false(self, tmp_path, temp_signal_path):
        """At 4 failures, spinning should NOT be triggered."""
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("""# Implementation Plan: Test

## Tasks

- [ ] **Task** (T001)
  Description

---
*Auto-generated*
""")

        original_signal_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            with patch("src.plan.IMPLEMENTATION_PLAN", plan_file):
                ralph = Ralph(project_path=str(tmp_path))
                ralph.load_plan()

                # Fail 4 times
                for _ in range(4):
                    temp_signal_path.write_text('{"pass": false}')
                    ralph.load_signal()
                    ralph.process_signal()

                # Spinning should NOT be triggered yet
                content = json.loads(temp_signal_path.read_text())
                assert content.get("spinning") is not True
        finally:
            Signal.SIGNAL_PATH = original_signal_path

    def test_spinning_at_five_failures_is_true(self, tmp_path, temp_signal_path):
        """At 5 failures, spinning SHOULD be triggered."""
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("""# Implementation Plan: Test

## Tasks

- [ ] **Task** (T001)
  Description

---
*Auto-generated*
""")

        original_signal_path = Signal.SIGNAL_PATH
        Signal.SIGNAL_PATH = temp_signal_path

        try:
            with patch("src.plan.IMPLEMENTATION_PLAN", plan_file):
                ralph = Ralph(project_path=str(tmp_path))
                ralph.load_plan()

                # Fail 5 times
                for _ in range(5):
                    temp_signal_path.write_text('{"pass": false}')
                    ralph.load_signal()
                    ralph.process_signal()

                # Spinning SHOULD be triggered
                content = json.loads(temp_signal_path.read_text())
                assert content.get("spinning") is True
        finally:
            Signal.SIGNAL_PATH = original_signal_path
