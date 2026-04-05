"""Tests for Ralph Dark Factory."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signal import Signal
from src.plan import Task, ImplementationPlan, generate_plan
from src.scenario_author import Scenario, Assertion, generate_scenarios


class TestSignal(unittest.TestCase):
    """Tests for signal handling."""

    def test_pass_signal(self):
        """Pass signal should serialize correctly."""
        signal = Signal.pass_signal()
        data = signal.to_dict()
        self.assertEqual(data, {"pass": True})

    def test_fail_signal(self):
        """Fail signal should serialize correctly."""
        signal = Signal.fail_signal()
        data = signal.to_dict()
        self.assertEqual(data, {"pass": False})

    def test_spinning_signal(self):
        """Spinning signal should serialize correctly."""
        signal = Signal.spinning_signal("test-task")
        data = signal.to_dict()
        self.assertEqual(data, {"spinning": True, "task": "test-task"})

    def test_done_signal(self):
        """Done signal should serialize correctly."""
        signal = Signal.done_signal()
        data = signal.to_dict()
        self.assertEqual(data, {"done": True})

    def test_signal_roundtrip(self):
        """Signal should survive round-trip serialization."""
        original = Signal.spinning_signal("my-task")
        # Write and read back
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(original.to_dict(), f)
            tmp_path = f.name

        with open(tmp_path) as f:
            data = json.load(f)
        os.unlink(tmp_path)

        restored = Signal.from_dict(data)
        self.assertEqual(restored.spinning, True)
        self.assertEqual(restored.task, "my-task")

    def test_no_leaky_content(self):
        """Signal should not contain scenario names or error details."""
        signal = Signal.fail_signal()
        data = signal.to_dict()

        # Should only contain "pass" key
        self.assertEqual(list(data.keys()), ["pass"])
        self.assertNotIn("error", data)
        self.assertNotIn("scenario", data)
        self.assertNotIn("message", data)


class TestPlan(unittest.TestCase):
    """Tests for plan generation."""

    def test_task_markdown(self):
        """Task should convert to markdown correctly."""
        task = Task(id="T001", title="Test Task", description="Description")
        md = task.to_markdown()
        self.assertIn("[ ]", md)
        self.assertIn("Test Task", md)
        self.assertIn("T001", md)

    def test_plan_pending_tasks(self):
        """Plan should return pending tasks correctly."""
        plan = ImplementationPlan("Test Project")
        plan.add_task("Task 1", "Desc 1")
        plan.add_task("Task 2", "Desc 2")
        plan.tasks[0].status = "done"

        pending = plan.get_pending_tasks()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].title, "Task 2")

    def test_plan_increment_retry(self):
        """Plan should track retry counts correctly."""
        plan = ImplementationPlan("Test Project")
        plan.add_task("Task 1", "Desc 1")

        count1 = plan.increment_retry("T001")
        self.assertEqual(count1, 1)

        count2 = plan.increment_retry("T001")
        self.assertEqual(count2, 2)


class TestScenarioAuthor(unittest.TestCase):
    """Tests for scenario authorship."""

    def test_assertion_to_dict(self):
        """Assertion should serialize correctly."""
        assertion = Assertion(
            type="http_status",
            path="/api/test",
            expect=200
        )
        data = assertion.to_dict()
        self.assertEqual(data["type"], "http_status")
        self.assertEqual(data["path"], "/api/test")
        self.assertEqual(data["expect"], 200)

    def test_scenario_to_dict(self):
        """Scenario should serialize correctly."""
        scenario = Scenario(name="Test Scenario")
        scenario.trigger = {"method": "POST", "path": "/api/test"}
        scenario.assertions.append(Assertion(type="http_status", path="/api/test", expect=200))

        data = scenario.to_dict()
        self.assertEqual(data["name"], "Test Scenario")
        self.assertEqual(data["trigger"]["method"], "POST")
        self.assertEqual(len(data["assertions"]), 1)


class TestFilesystemIsolation(unittest.TestCase):
    """Tests for filesystem isolation."""

    def test_scenarios_dir_permissions(self):
        """Scenarios directory should have restricted permissions."""
        scenarios_dir = Path("scenarios")
        if scenarios_dir.exists():
            mode = os.stat(scenarios_dir).st_mode & 0o777
            # Should be owner-only (0o700) or similar restrictive mode
            self.assertEqual(mode, 0o700)


if __name__ == "__main__":
    unittest.main()
