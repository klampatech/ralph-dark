"""Scenario authorship - generates scenarios from specs.

This module generates scenarios/*.yaml from specs/*.md.
It does NOT read IMPLEMENTATION_PLAN.md (filesystem isolation enforced).
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

SPECS_DIR = Path("specs")
SCENARIOS_DIR = Path("scenarios")


@dataclass
class Assertion:
    """Represents a scenario assertion."""

    type: str
    path: Optional[str] = None
    expect: Optional[Any] = None
    table: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert assertion to dictionary."""
        result = {"type": self.type}
        if self.path:
            result["path"] = self.path
        if self.expect is not None:
            result["expect"] = self.expect
        if self.table:
            result["table"] = self.table
        if self.conditions:
            result["conditions"] = self.conditions
        return result


@dataclass
class Scenario:
    """Represents a test scenario."""

    name: str
    trigger: Optional[Dict[str, Any]] = None
    env: Dict[str, str] = field(default_factory=dict)
    assertions: List[Assertion] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert scenario to dictionary."""
        result = {"name": self.name}
        if self.trigger:
            result["trigger"] = self.trigger
        if self.env:
            result["env"] = self.env
        if self.assertions:
            result["assertions"] = [a.to_dict() for a in self.assertions]
        return result

    def to_yaml(self) -> str:
        """Convert scenario to YAML format."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)


def extract_scenarios_from_spec(spec_content: str) -> List[Scenario]:
    """Extract scenarios from spec content."""
    scenarios = []

    import re

    # Find all scenario sections
    scenario_pattern = re.compile(
        r"## Scenario: (.+?)(?=\n##|\Z)", re.DOTALL
    )

    for match in scenario_pattern.finditer(spec_content):
        title = match.group(1).strip().split("\n")[0]
        body = match.group(1)

        scenario = Scenario(name=title)

        # Parse Given/When/Then
        given_match = re.search(r"Given\s+(.+?)(?:\n|$)", body)
        when_match = re.search(r"When\s+(.+?)(?:\n|$)", body)
        then_match = re.search(r"Then\s+(.+?)(?:\n|$)", body)

        # Parse trigger (usually in When)
        if when_match:
            when_text = when_match.group(1).strip()
            if "POST" in when_text:
                # Extract POST /api/endpoint { body }
                post_match = re.search(r"POST\s+(/api/\S+)\s*\{(.+)\}", when_text)
                if post_match:
                    path = post_match.group(1)
                    body_str = post_match.group(2).strip()
                    scenario.trigger = {
                        "method": "POST",
                        "path": path,
                        "body": body_str
                    }

        # Parse assertions (usually in Then)
        if then_match:
            then_text = then_match.group(1).strip()

            # HTTP status assertion
            if "http_status" in then_text or "status is" in then_text:
                path_match = re.search(r'path["\s]+(/\S+)', then_text)
                expect_match = re.search(r"expect[s]?\s+(\d+)", then_text)
                if path_match and expect_match:
                    scenario.assertions.append(Assertion(
                        type="http_status",
                        path=path_match.group(1),
                        expect=int(expect_match.group(1))
                    ))

            # DB record assertion
            if "db_record" in then_text or "queries" in then_text:
                table_match = re.search(r'table["\s]+(\w+)', then_text)
                conditions_match = re.search(r"conditions?[:\s]+\{(.+)\}", then_text)
                if table_match:
                    conditions = {}
                    if conditions_match:
                        cond_str = conditions_match.group(1)
                        key_val_matches = re.findall(r'"(\w+)":\s*"?([^",]+)"?', cond_str)
                        for k, v in key_val_matches:
                            conditions[k] = v.strip()
                    scenario.assertions.append(Assertion(
                        type="db_record",
                        table=table_match.group(1),
                        conditions=conditions
                    ))

        scenarios.append(scenario)

    return scenarios


def generate_scenarios() -> List[Scenario]:
    """Generate scenarios from spec files.

    This function reads specs/*.md but does NOT read IMPLEMENTATION_PLAN.md.
    """
    all_scenarios = []

    if not SPECS_DIR.exists():
        return all_scenarios

    for spec_file in sorted(SPECS_DIR.glob("*.md")):
        try:
            content = spec_file.read_text()
            scenarios = extract_scenarios_from_spec(content)
            all_scenarios.extend(scenarios)
        except Exception:
            continue

    return all_scenarios


def save_scenarios(scenarios: List[Scenario]) -> None:
    """Save scenarios to scenarios/*.yaml files."""
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

    # Clear existing scenarios
    for f in SCENARIOS_DIR.glob("*.yaml"):
        f.unlink()

    for i, scenario in enumerate(scenarios):
        filename = SCENARIOS_DIR / f"scenario_{i:03d}.yaml"
        filename.write_text(scenario.to_yaml())


def load_scenarios() -> List[Scenario]:
    """Load all scenarios from scenarios/*.yaml."""
    if not SCENARIOS_DIR.exists():
        return []

    scenarios = []
    for f in sorted(SCENARIOS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text())
            scenario = Scenario(name=data.get("name", f.stem))
            if "trigger" in data:
                scenario.trigger = data["trigger"]
            if "env" in data:
                scenario.env = data["env"]
            if "assertions" in data:
                for a in data["assertions"]:
                    scenario.assertions.append(Assertion(
                        type=a.get("type", ""),
                        path=a.get("path"),
                        expect=a.get("expect"),
                        table=a.get("table"),
                        conditions=a.get("conditions")
                    ))
            scenarios.append(scenario)
        except Exception:
            continue

    return scenarios
