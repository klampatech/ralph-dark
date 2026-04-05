"""Scenario harness for executing YAML scenario files against a running system."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from harness.db import assert_db_record

SIGNAL_FILE = Path("/tmp/ralph-scenario-result.json")
SCENARIOS_DIR = Path("scenarios")


def load_signal() -> dict[str, Any] | None:
    """Load the signal file if it exists."""
    if not SIGNAL_FILE.exists():
        return None
    try:
        with open(SIGNAL_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def write_result(passed: bool) -> None:
    """Write the result signal file.

    Args:
        passed: Whether all scenarios passed.
    """
    with open(SIGNAL_FILE, "w") as f:
        json.dump({"pass": passed}, f)


def check_http_status(url: str, expected: int) -> bool:
    """Check HTTP response status code.

    Args:
        url: URL to check.
        expected: Expected status code.

    Returns:
        True if status matches expected, False otherwise.
    """
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status == expected
    except Exception:
        return False


def check_db_record(query: str, expected_rows: int | None = None) -> bool:
    """Check database record assertion.

    Args:
        query: SQL query to execute.
        expected_rows: Expected number of rows.

    Returns:
        True if assertion passes, False otherwise.
    """
    return assert_db_record(query, expected_rows)


def run_assertion(assertion: dict[str, Any]) -> bool:
    """Run a single assertion.

    Args:
        assertion: Assertion configuration.

    Returns:
        True if assertion passes, False otherwise.
    """
    if "http_status" in assertion:
        http_conf = assertion["http_status"]
        return check_http_status(http_conf["url"], http_conf["expected"])

    if "db_record" in assertion:
        db_conf = assertion["db_record"]
        return check_db_record(db_conf["query"], db_conf.get("expected_rows"))

    return False


def load_scenarios() -> list[dict[str, Any]]:
    """Load all YAML scenario files.

    Returns:
        List of scenario dictionaries.
    """
    scenarios = []

    if not SCENARIOS_DIR.exists():
        return scenarios

    for yaml_file in SCENARIOS_DIR.glob("*.yaml"):
        try:
            with open(yaml_file) as f:
                scenarios.append(yaml.safe_load(f))
        except (yaml.YAMLError, OSError):
            continue

    return scenarios


def run_scenarios() -> None:
    """Execute all scenarios and write aggregated result."""
    signal = load_signal()

    if signal is None or not isinstance(signal, dict):
        write_result(False)
        return

    scenarios = load_scenarios()

    if not scenarios:
        write_result(True)
        return

    all_passed = True

    for scenario in scenarios:
        if "assertions" not in scenario:
            continue

        for assertion in scenario["assertions"]:
            if not run_assertion(assertion):
                all_passed = False
                break

        if not all_passed:
            break

    write_result(all_passed)


if __name__ == "__main__":
    run_scenarios()