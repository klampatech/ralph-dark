"""Signal handling for Ralph scenario execution.

This module manages the signal file at /tmp/ralph-scenario-result.json
which communicates pass/fail state to Ralph between iterations.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SIGNAL_PATH = Path("/tmp/ralph-scenario-result.json")


@dataclass
class Signal:
    """Represents a scenario execution signal."""

    SIGNAL_PATH: Path = None  # type: ignore[assignment]

    pass_result: Optional[bool] = None
    spinning: bool = False
    task: Optional[str] = None
    done: bool = False

    def __post_init__(self):
        """Initialize SIGNAL_PATH if not set."""
        if self.SIGNAL_PATH is None:
            Signal.SIGNAL_PATH = SIGNAL_PATH

    @classmethod
    def _get_signal_path(cls) -> Path:
        """Get the current signal path, checking class then module."""
        # Check if class attribute is a valid Path (not None)
        if isinstance(cls.SIGNAL_PATH, Path):
            return cls.SIGNAL_PATH
        # Fall back to module-level SIGNAL_PATH
        import src.signal as signal_module
        return signal_module.SIGNAL_PATH

    def to_dict(self) -> dict:
        """Convert signal to dictionary for JSON serialization."""
        if self.spinning:
            return {"spinning": True, "task": self.task}
        if self.done:
            return {"done": True}
        if self.pass_result is not None:
            return {"pass": self.pass_result}
        return {"pass": False}

    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        """Create Signal from dictionary."""
        signal = cls()
        if "pass" in data:
            signal.pass_result = data["pass"]
        if "spinning" in data:
            signal.spinning = data["spinning"]
            signal.task = data.get("task")
        if "done" in data:
            signal.done = data["done"]
        return signal

    @classmethod
    def read(cls) -> "Signal":
        """Read signal from the signal file."""
        path = cls.SIGNAL_PATH if isinstance(cls.SIGNAL_PATH, Path) else SIGNAL_PATH
        if not path.exists():
            return cls(pass_result=False)
        try:
            content = path.read_text()
            data = json.loads(content)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return cls(pass_result=False)

    def write(self) -> None:
        """Write signal to the signal file."""
        path = Signal.SIGNAL_PATH if isinstance(Signal.SIGNAL_PATH, Path) else SIGNAL_PATH
        content = json.dumps(self.to_dict(), separators=(",", ":"))
        path.write_text(content)

    @classmethod
    def pass_signal(cls) -> "Signal":
        """Create a passing signal."""
        signal = cls()
        signal.pass_result = True
        return signal

    @classmethod
    def fail_signal(cls) -> "Signal":
        """Create a failing signal."""
        signal = cls()
        signal.pass_result = False
        return signal

    @classmethod
    def spinning_signal(cls, task: str) -> "Signal":
        """Create a spinning signal."""
        signal = cls()
        signal.spinning = True
        signal.task = task
        return signal

    @classmethod
    def done_signal(cls) -> "Signal":
        """Create a done signal."""
        signal = cls()
        signal.done = True
        return signal
