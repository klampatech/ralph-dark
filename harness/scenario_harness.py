"""Scenario harness for executing YAML scenario files against a running system."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from harness.db import assert_db_record, execute_query, build_select_query

SIGNAL_FILE = Path("/tmp/ralph-scenario-result.json")
SCENARIOS_DIR = Path("scenarios")
DEFAULT_BASE_URL = "http://localhost:8080"


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
        url: Full URL to check.
        expected: Expected status code.

    Returns:
        True if status matches expected, False otherwise.
    """
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status == expected
    except urllib.error.HTTPError as e:
        return e.code == expected
    except Exception:
        return False


def check_http_status_by_path(base_url: str, path: str, expected: int) -> bool:
    """Check HTTP response status code for a given path.

    Args:
        base_url: Base URL of the running system.
        path: URL path to check.
        expected: Expected status code.

    Returns:
        True if status matches expected, False otherwise.
    """
    url = f"{base_url.rstrip('/')}{path}"
    return check_http_status(url, expected)


def check_db_record(
    query: str | None = None,
    table: str | None = None,
    conditions: dict[str, Any] | None = None,
    expected_rows: int | None = None
) -> bool:
    """Check database record assertion.

    Supports two formats:
    1. query-based: pass query string directly
    2. table+conditions: pass table name and conditions dict

    Args:
        query: SQL query to execute (legacy format).
        table: Table name to query (new format).
        conditions: Dict of column -> value conditions (new format).
        expected_rows: Expected number of rows.

    Returns:
        True if assertion passes, False otherwise.
    """
    if table is not None and conditions is not None:
        # New format: build query from table and conditions
        query = build_select_query(table, conditions)

    if query is None:
        return False

    return assert_db_record(query, expected_rows)


def run_assertion(assertion: dict[str, Any], base_url: str = DEFAULT_BASE_URL) -> bool:
    """Run a single assertion.


    Args:
        assertion: Assertion configuration. Supports two formats:
            1. Nested: {"http_status": {"path": "...", "expect": ...}}
            2. Flat: {"type": "http_status", "path": "...", "expect": ...}
        base_url: Base URL for HTTP assertions.

    Returns:
        True if assertion passes, False otherwise.
    """
    # Handle flat format: { "type": "http_status", "path": "...", "expect": ... }
    if "type" in assertion:
        assertion_type = assertion["type"]
        if assertion_type == "http_status":
            return check_http_status_by_path(
                base_url, assertion["path"], assertion["expect"]
            )
        elif assertion_type == "db_record":
            query = assertion.get("query")
            expected_rows = assertion.get("expected_rows")
            table = assertion.get("table")
            conditions = assertion.get("conditions")
            if table is not None and conditions is not None:
                return check_db_record(table=table, conditions=conditions)
            elif query:
                return check_db_record(query=query, expected_rows=expected_rows)
        return False

    # Handle nested format: {"http_status": {"path": "...", "expect": ...}}
    if "http_status" in assertion:
        http_conf = assertion["http_status"]
        if "url" in http_conf:
            return check_http_status(http_conf["url"], http_conf["expected"])
        elif "path" in http_conf:
            return check_http_status_by_path(base_url, http_conf["path"], http_conf["expected"])

    if "db_record" in assertion:
        db_conf = assertion["db_record"]
        if "query" in db_conf:
            return check_db_record(query=db_conf["query"], expected_rows=db_conf.get("expected_rows"))
        elif "table" in db_conf and "conditions" in db_conf:
            return check_db_record(table=db_conf["table"], conditions=db_conf["conditions"])
        return False

    return False


def load_scenarios() -> list[dict[str, Any]]:
    """Load all YAML scenario files.

    Returns:
        List of scenario dictionaries.
    """
    scenarios = []

    if not SCENARIOS_DIR.exists():
        return scenarios

    for yaml_file in sorted(SCENARIOS_DIR.glob("*.yaml")):
        try:
            with open(yaml_file) as f:
                scenarios.append(yaml.safe_load(f))
        except (yaml.YAMLError, OSError):
            continue

    return scenarios


def load_scenario_from_file(filepath: Path) -> dict[str, Any] | None:
    """Load a single scenario from a YAML file.

    Args:
        filepath: Path to the scenario file.

    Returns:
        Scenario dictionary or None if failed.
    """
    try:
        with open(filepath) as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
        return None


def run_trigger(trigger: dict[str, Any], base_url: str = DEFAULT_BASE_URL) -> None:
    """Execute a scenario trigger (HTTP request).

    Args:
        trigger: Trigger configuration with method, path, and body.
        base_url: Base URL of the running system.
    """
    if not trigger:
        return

    method = trigger.get("method", "GET").upper()
    path = trigger.get("path", "/")
    body = trigger.get("body")

    url = f"{base_url.rstrip('/')}{path}"

    data = None
    if body:
        if isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            pass
    except urllib.error.HTTPError:
        pass
    except urllib.error.URLError:
        pass


def run_scenario(scenario: dict[str, Any], base_url: str = DEFAULT_BASE_URL) -> bool:
    """Execute a single scenario.


    Args:
        scenario: Scenario dictionary with trigger and assertions.
        base_url: Base URL of the running system.

    Returns:
        True if all assertions pass, False otherwise.
    """
    # Execute trigger if present
    if "trigger" in scenario:
        run_trigger(scenario["trigger"], base_url)

    # Execute assertions
    if "assertions" not in scenario:
        return True

    for assertion in scenario["assertions"]:
        if not run_assertion(assertion, base_url):
            return False

    return True


class Harness:
    """Executes scenarios against the running system."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url
        self.results: list[dict[str, Any]] = []

    def execute_trigger(self, trigger: dict[str, Any]) -> None:
        """Execute a trigger."""
        run_trigger(trigger, self.base_url)

    def check_http_status(self, path: str, expected: int) -> bool:
        """Check HTTP status for a path."""
        return check_http_status_by_path(self.base_url, path, expected)

    def check_db_record(
        self,
        query: str | None = None,
        table: str | None = None,
        conditions: dict[str, Any] | None = None,
        expected_rows: int | None = None
    ) -> bool:
        """Check database record assertion.

        Supports two formats:
        1. query-based: pass query string directly
        2. table+conditions: pass table name and conditions dict

        Args:
            query: SQL query to execute (legacy format).
            table: Table name to query (new format).
            conditions: Dict of column -> value conditions (new format).
            expected_rows: Expected number of rows.

        Returns:
            True if assertion passes, False otherwise.
        """
        return check_db_record(query, table, conditions, expected_rows)


    def execute_scenario(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Execute a single scenario.

        Args:
            scenario: Scenario dictionary.

        Returns:
            Result dict with name and passed status.
        """
        name = scenario.get("name", "unnamed")
        passed = run_scenario(scenario, self.base_url)
        return {"name": name, "passed": passed}

    def execute_all(self) -> list[dict[str, Any]]:
        """Execute all scenarios.

        Returns:
            List of result dictionaries.
        """
        self.results = []
        scenarios = load_scenarios()

        for scenario in scenarios:
            result = self.execute_scenario(scenario)
            self.results.append(result)

        return self.results


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