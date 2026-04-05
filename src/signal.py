"""Signal handling for Ralph scenario execution.

This module manages the signal file at /tmp/ralph-scenario-result.json
which communicates pass/fail state to Ralph between iterations.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SIGNAL_PATH = Path("/tmp/ralph-scenario-result.json")


class Signal:
    """Represents a scenario execution signal."""

    # Class attribute for signal path - initialized to module level default
    SIGNAL_PATH: Optional[Path] = None

    def __init__(
        self,
        pass_result: Optional[bool] = None,
        spinning: bool = False,
        task: Optional[str] = None,
        done: bool = False,
    ):
        """Initialize signal with given values."""
        self.pass_result = pass_result
        self.spinning = spinning
        self.task = task
        self.done = done
        # Initialize SIGNAL_PATH on first instance if not set
        if Signal.SIGNAL_PATH is None:
            Signal.SIGNAL_PATH = SIGNAL_PATH

    @classmethod
    def _get_signal_path(cls) -> Path:
        """Get the current signal path, checking class then module."""
        # Check if class attribute has been properly initialized (not None)
        if cls.SIGNAL_PATH is not None:
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
    def _is_valid_signal_schema(cls, data: dict) -> bool:
        """Check if signal data matches a valid signal schema.
        
        Valid schemas are:
        - {"pass": true/false}
        - {"spinning": true, "task": "..."}
        - {"done": true}
        
        Args:
            data: Parsed JSON data.
            
        Returns:
            True if schema is valid, False otherwise.
        """
        if not isinstance(data, dict):
            return False
        
        # Check for valid pass signal: {"pass": true} or {"pass": false}
        if "pass" in data:
            return isinstance(data["pass"], bool)
        
        # Check for valid spinning signal: {"spinning": true, "task": "..."}
        if "spinning" in data:
            return data["spinning"] is True and "task" in data
        
        # Check for valid done signal: {"done": true}
        if "done" in data:
            return data["done"] is True
        
        return False

    @classmethod
    def read(cls) -> "Signal":
        """Read signal from the signal file.
        
        Returns a Signal with pass_result=False for:
        - Missing file
        - Malformed JSON
        - Invalid signal schema
        """
        path = cls.SIGNAL_PATH if cls.SIGNAL_PATH is not None else SIGNAL_PATH
        if not path.exists():
            return cls(pass_result=False)
        try:
            content = path.read_text()
            data = json.loads(content)
            # Validate signal schema - malformed schema treated as fail
            if not cls._is_valid_signal_schema(data):
                return cls(pass_result=False)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return cls(pass_result=False)

    def write(self) -> None:
        """Write signal to the signal file."""
        path = self._get_signal_path()
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
