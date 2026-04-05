"""Scenario harness - executes scenarios and writes signals.

The harness reads scenarios/*.yaml and executes them against the running system,
then writes pass/fail signal to /tmp/ralph-scenario-result.json.
"""

import json
import sqlite3
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from .scenario_author import Scenario, load_scenarios, Assertion
from .signal import Signal

SCENARIOS_DIR = Path("scenarios")
DB_PATH = Path("ralph.db")


@dataclass
class HarnessResult:
    """Result of a scenario execution."""

    scenario_name: str
    passed: bool
    error: Optional[str] = None


class Harness:
    """Executes scenarios against the running system."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self.results: List[HarnessResult] = []

    def execute_scenario(self, scenario: Scenario) -> HarnessResult:
        """Execute a single scenario."""
        try:
            # Apply environment variables
            env_vars = scenario.env.copy()

            # Execute trigger if present
            if scenario.trigger:
                self._execute_trigger(scenario.trigger)

            # Execute assertions
            for assertion in scenario.assertions:
                if not self._execute_assertion(assertion):
                    return HarnessResult(
                        scenario_name=scenario.name,
                        passed=False,
                        error=f"Assertion failed: {assertion.type}"
                    )

            return HarnessResult(scenario_name=scenario.name, passed=True)

        except Exception as e:
            return HarnessResult(
                scenario_name=scenario.name,
                passed=False,
                error=str(e)
            )

    def _execute_trigger(self, trigger: Dict[str, Any]) -> None:
        """Execute a scenario trigger (HTTP request)."""
        method = trigger.get("method", "GET").upper()
        path = trigger.get("path", "/")
        body = trigger.get("body")

        url = f"{self.base_url}{path}"

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
        except urllib.error.HTTPError as e:
            # HTTP errors are expected for some tests
            pass
        except urllib.error.URLError:
            # System not running - this is expected in some scenarios
            pass

    def _execute_assertion(self, assertion: Assertion) -> bool:
        """Execute a single assertion."""
        if assertion.type == "http_status":
            return self._assert_http_status(assertion)
        elif assertion.type == "db_record":
            return self._assert_db_record(assertion)
        return True

    def _assert_http_status(self, assertion: Assertion) -> bool:
        """Assert HTTP status code."""
        path = assertion.path or "/"
        expected = assertion.expect

        url = f"{self.base_url}{path}"

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as response:
                actual = response.getcode()
                return actual == expected
        except urllib.error.HTTPError as e:
            return e.code == expected
        except urllib.error.URLError:
            # If we can't connect, assume system not running
            return False

    def _assert_db_record(self, assertion: Assertion) -> bool:
        """Assert database record exists."""
        table = assertion.table
        conditions = assertion.conditions or {}

        if not DB_PATH.exists():
            return False

        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            # Build WHERE clause
            where_parts = [f"{k} = ?" for k in conditions.keys()]
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"
            values = list(conditions.values())

            query = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
            cursor.execute(query, values)

            count = cursor.fetchone()[0]
            conn.close()

            return count > 0

        except Exception:
            return False

    def execute_all(self) -> List[HarnessResult]:
        """Execute all scenarios."""
        self.results = []
        scenarios = load_scenarios()

        for scenario in scenarios:
            result = self.execute_scenario(scenario)
            self.results.append(result)

        return self.results

    def write_signal(self) -> None:
        """Write aggregated signal to file."""
        # Determine pass/fail - all must pass
        all_passed = all(r.passed for r in self.results)
        # Any failures means fail
        any_failed = any(not r.passed for r in self.results)

        if any_failed:
            signal = Signal.fail_signal()
        else:
            signal = Signal.pass_signal()

        signal.write()


def run_harness() -> Harness:
    """Run the harness and return the harness instance.

    Caller is responsible for calling write_signal() after inspecting results.
    """
    harness = Harness()
    harness.execute_all()
    return harness
