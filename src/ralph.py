"""Ralph agent - autonomous coding agent with hidden scenario loop.

Ralph is an AI coding agent that:
1. Reads specs from specs/*.md
2. Generates IMPLEMENTATION_PLAN.md (without reading scenarios/)
3. Generates scenarios/*.yaml (without reading IMPLEMENTATION_PLAN.md)
4. Executes scenarios via post-commit hook
5. Reads signal from /tmp/ralph-scenario-result.json
6. Advances tasks on pass, retries on fail
7. Detects spinning (5+ retries) and notifies operator
"""

import os
import sys
from pathlib import Path

# Prevent reading from scenarios/ directory (filesystem isolation)
SCENARIOS_DIR = Path("scenarios")


def deny_scenarios_access() -> bool:
    """Check if scenarios/ exists and should be protected."""
    if SCENARIOS_DIR.exists():
        # Set restrictive permissions to deny read access
        try:
            os.chmod(SCENARIOS_DIR, 0o700)  # rwx------ - only owner can access
            for f in SCENARIOS_DIR.glob("*.yaml"):
                os.chmod(f, 0o600)  # rw------- - only owner can read
            return True
        except OSError:
            pass
    return False


class Ralph:
    """Ralph autonomous agent."""

    SPINNING_THRESHOLD = 5

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.plan = None
        self.signal = None
        self.current_task = None

    def load_plan(self):
        """Load implementation plan."""
        from .plan import load_plan, generate_plan, save_plan

        try:
            self.plan = load_plan()
        except Exception:
            self.plan = generate_plan()
            save_plan(self.plan)

    def load_signal(self):
        """Load the current signal."""
        from .signal import Signal
        self.signal = Signal.read()

    def check_spinning(self) -> bool:
        """Check if current task is spinning (5+ retries)."""
        if not self.current_task:
            return False
        return self.current_task.retry_count >= self.SPINNING_THRESHOLD

    def process_signal(self) -> None:
        """Process the signal and update task state."""
        if not self.plan or not self.current_task:
            return

        if self.signal.spinning:
            # Already spinning - operator should intervene
            return

        if self.signal.pass_result is True:
            # Task passed - mark done and advance
            self.plan.mark_done(self.current_task.id)
            self.current_task = self.plan.get_current_task()
        elif self.signal.pass_result is False:
            # Task failed - increment retry
            retry_count = self.plan.increment_retry(self.current_task.id)
            if retry_count >= self.SPINNING_THRESHOLD:
                # Mark as spinning
                from .signal import Signal
                spinning_signal = Signal.spinning_signal(self.current_task.title)
                spinning_signal.write()
                self.signal = spinning_signal

    def get_current_task(self):
        """Get current task for execution."""
        if not self.plan:
            self.load_plan()
        self.current_task = self.plan.get_current_task()
        return self.current_task

    def is_done(self) -> bool:
        """Check if all tasks are complete."""
        if not self.plan:
            return False
        return self.plan.get_current_task() is None

    def mark_done(self) -> None:
        """Mark all tasks as done and write done signal."""
        from .plan import save_plan
        from .signal import Signal

        if self.plan:
            for task in self.plan.tasks:
                task.status = "done"
            save_plan(self.plan)

        done_signal = Signal.done_signal()
        done_signal.write()

    def enforce_isolation(self) -> None:
        """Enforce filesystem isolation for scenarios/."""
        deny_scenarios_access()
