"""Signal writer for Ralph scenario feedback loop.

Writes only clean JSON signals to /tmp/ralph-scenario-result.json.
Never leaks scenario names, error messages, or stack traces.
"""

import json
from pathlib import Path

SIGNAL_PATH = Path("/tmp/ralph-scenario-result.json")

# Valid signal schemas only
_VALID_SIGNALS = (
    {"pass": True},
    {"pass": False},
    {"spinning": True, "task": "..."},
    {"done": True},
)


def write_signal(signal: dict) -> None:
    """Write a validated signal to the signal file.

    Only four signal forms are allowed:
    - {"pass": true}
    - {"pass": false}
    - {"spinning": true, "task": "..."}
    - {"done": true}

    Args:
        signal: The signal dict to write.

    Raises:
        ValueError: If the signal does not match an allowed schema.
    """
    if signal not in _VALID_SIGNALS:
        raise ValueError("Invalid signal schema")

    with open(SIGNAL_PATH, "w") as f:
        json.dump(signal, f)


def read_signal() -> dict:
    """Read the current signal from the signal file.

    Returns:
        The current signal dict, or {"pass": false} if missing or malformed.
    """
    try:
        with open(SIGNAL_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"pass": False}
