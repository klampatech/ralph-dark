#!/bin/bash
# Ralph Dark Factory Scenario Loop
# Main entry point for plan mode, scenario authorship, and build mode

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIGNAL_FILE="/tmp/ralph-scenario-result.json"
IMPLEMENTATION_PLAN="IMPLEMENTATION_PLAN.md"

usage() {
    echo "Ralph Dark Factory Scenario Loop"
    echo ""
    echo "Usage: ./loop.sh <command> [options]"
    echo ""
    echo "Commands:"
    echo "  plan --project <name>     Generate IMPLEMENTATION_PLAN.md from specs/*.md"
    echo "  scenario-authorship       Generate scenarios/*.yaml from specs"
    echo "  build                     Run build mode (requires operator invocation)"
    echo "  run-scenarios             Execute harness and write signal"
    echo "  signal                    Read and display current signal"
    echo ""
    echo "Options:"
    echo "  --project <name>          Project name for plan generation"
}

# Ensure we have a command
if [[ $# -eq 0 ]]; then
    usage
    exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
    plan)
        PROJECT_NAME=" Ralph Dark Factory"
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --project)
                    PROJECT_NAME="$2"
                    shift 2
                    ;;
                *)
                    echo "Unknown option: $1"
                    usage
                    exit 1
                    ;;
            esac
        done

        echo "Generating IMPLEMENTATION_PLAN.md..."
        python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR/src')
from plan import generate_plan, save_plan
plan = generate_plan()
plan.project_name = '$PROJECT_NAME'
save_plan(plan)
print('Implementation plan generated.')
"
        echo "Plan review gate: Review IMPLEMENTATION_PLAN.md before running build mode."
        ;;

    scenario-authorship)
        echo "Generating scenarios from specs..."
        # Read specs and generate scenario YAML files
        python3 -c "
import sys
import yaml
import re
from pathlib import Path

SPECS_DIR = Path('$SCRIPT_DIR/specs')
SCENARIOS_DIR = Path('$SCRIPT_DIR/scenarios')
SCENARIOS_DIR.mkdir(exist_ok=True)

for spec_file in sorted(SPECS_DIR.glob('*.md')):
    content = spec_file.read_text()
    feature_match = re.search(r'#\s*Feature:\s*(.+)', content)
    feature_name = feature_match.group(1).strip() if feature_match else 'unnamed'

    scenario_pattern = re.compile(r'##\s*Scenario:\s*(.+?)(?=\n##|\Z)', re.DOTALL)
    for i, match in enumerate(scenario_pattern.finditer(content)):
        scenario_name = match.group(1).strip().split('\n')[0][:50]
        given_when_then = re.findall(r'(Given|When|Then|And)\s+(.+?)(?=\n(?:Given|When|Then|And)|$)', match.group(1), re.DOTALL)

        scenario = {
            'name': scenario_name.lower().replace(' ', '-'),
            'trigger': {
                'type': 'http',
                'method': 'GET',
                'path': '/health'
            },
            'assertions': [
                {
                    'type': 'http_status',
                    'expect': 200
                }
            ]
        }

        output_file = SCENARIOS_DIR / f'scenario_{i:03d}.yaml'
        output_file.write_text(yaml.dump(scenario, default_flow_style=False))
        print(f'Generated: {output_file}')
"
        echo "Scenario review gate: Review scenarios/*.yaml before running build mode."
        ;;

    build)
        if [[ ! -f "$IMPLEMENTATION_PLAN" ]]; then
            echo "Error: IMPLEMENTATION_PLAN.md not found. Run './loop.sh plan --project <name>' first."
            exit 1
        fi
        echo "Build mode: This would run the Ralph agent loop."
        echo "Operator gate: Build mode waits for explicit invocation."
        ;;

    run-scenarios)
        echo "Running scenario harness..."
        bash "$SCRIPT_DIR/.orch/harness.sh" "$SCRIPT_DIR/scenarios" "$SIGNAL_FILE"
        echo "Signal: $(cat "$SIGNAL_FILE")"
        ;;

    signal)
        if [[ -f "$SIGNAL_FILE" ]]; then
            echo "Current signal: $(cat "$SIGNAL_FILE")"
        else
            echo "No signal file found."
        fi
        ;;

    *)
        echo "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac
