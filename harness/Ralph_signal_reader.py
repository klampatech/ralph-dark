"""Signal reader for Ralph scenario feedback loop.

Reads /tmp/ralph-scenario-result.json and interprets signals
to return appropriate actions: "advance", "retry", "spinning", "done".
Treats missing/malformed signals as {"pass": false}.
"""

import json
from pathlib import Path

from .signal import read_signal

SIGNAL_PATH = Path("/tmp/ralph-scenario-result.json")

# Signal to action mapping
_ACTION_MAP = {
    ("pass", True): "advance",
    ("pass", False): "retry",
    ("spinning", True): "spinning",
    ("done", True): "done",
}


def interpret_signal(signal: dict | None = None) -> str:
    """Interpret a signal and return the appropriate Ralph action.

    Args:
        signal: Optional signal dict. If None, reads from SIGNAL_PATH.

    Returns:
        One of: "advance", "retry", "spinning", "done".
        Defaults to "retry" for missing or malformed signals.
    """
    if signal is None:
        signal = _read_signal_file()

    if not isinstance(signal, dict):
        return "retry"

    if signal == {"pass": True}:
        return "advance"
    if signal == {"pass": False}:
        return "retry"
    if signal == {"done": True}:
        return "done"

    spinning = signal.get("spinning")
    if spinning is True:
        return "spinning"

    return "retry"


def _read_signal_file() -> dict:
    """Read the signal file from disk.

    Returns:
        The parsed JSON dict, or {"pass": false} if missing/malformed.
    """
    try:
        with open(SIGNAL_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"pass": False}
