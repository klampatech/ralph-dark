"""Filesystem isolation for Ralph scenario protection.

Implements OS-level permissions to deny read access to the scenarios/ directory
by the Ralph process.
"""

import os
import stat
from pathlib import Path

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


def apply_isolation() -> None:
    """Revoke read permission on the scenarios directory.

    Uses chmod to remove all permissions (owner, group, others) from the
    scenarios directory, making it inaccessible to the current process.
    """
    if not SCENARIOS_DIR.exists():
        return

    # Remove all permissions: read, write, execute for owner, group, others
    os.chmod(SCENARIOS_DIR, stat.S_IRUSR & ~stat.S_IRUSR)


def remove_isolation() -> None:
    """Restore default permissions on the scenarios directory."""
    if not SCENARIOS_DIR.exists():
        return

    # Restore read permission for owner only
    os.chmod(SCENARIOS_DIR, stat.S_IRUSR)


def is_isolation_active() -> bool:
    """Check whether filesystem isolation is currently in place.

    Returns:
        True if the scenarios directory is not readable, False otherwise.
    """
    if not SCENARIOS_DIR.exists():
        return False

    return not os.access(SCENARIOS_DIR, os.R_OK)
