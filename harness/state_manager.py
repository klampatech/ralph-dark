"""State manager for Ralph scenario retry tracking.

Manages retry counts per task in state/retry_state.json.
Detects spinning (retry count > 5 for same task).
Persists state across restarts.
"""

import json
import threading
from pathlib import Path

STATE_DIR = Path(__file__).parent.parent / "state"
RETRY_STATE_FILE = STATE_DIR / "retry_state.json"
SPIN_THRESHOLD = 5

_local = threading.local()


def _get_state() -> dict:
    """Load or initialize the retry state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if RETRY_STATE_FILE.exists():
        try:
            with open(RETRY_STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    return {}


def _save_state(state: dict) -> None:
    """Persist the retry state to disk."""
    with open(RETRY_STATE_FILE, "w") as f:
        json.dump(state, f)


def get_retry_count(task: str) -> int:
    """Get the current retry count for a task.

    Args:
        task: The task identifier.

    Returns:
        The number of retries attempted for this task.
    """
    state = _get_state()
    return state.get(task, 0)


def increment_retry_count(task: str) -> int:
    """Increment and persist the retry count for a task.

    Args:
        task: The task identifier.

    Returns:
        The new retry count after incrementing.
    """
    state = _get_state()
    state[task] = state.get(task, 0) + 1
    _save_state(state)
    return state[task]


def reset_retry_count(task: str) -> None:
    """Reset the retry count for a task to zero.

    Args:
        task: The task identifier.
    """
    state = _get_state()
    if task in state:
        del state[task]
        _save_state(state)


def is_spinning(task: str) -> bool:
    """Check whether a task is spinning (exceeded retry threshold).

    Args:
        task: The task identifier.

    Returns:
        True if retry count exceeds SPIN_THRESHOLD, False otherwise.
    """
    return get_retry_count(task) > SPIN_THRESHOLD
