#!/bin/bash
# loop.sh - Plan mode execution script
#
# Usage:
#   ./loop.sh plan --project myproject   Generate implementation plan for review
#   ./loop.sh build --project myproject  Run build mode (requires operator approval)
#   ./loop.sh scenarios --project myproject  Generate scenarios for review

set -e

PROJECT=""
COMMAND=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        plan|build|scenarios)
            COMMAND="$1"
            shift
            ;;
        --project)
            PROJECT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ -z "$PROJECT" ]]; then
    echo "Error: --project is required"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RALPH_BIN="$SCRIPT_DIR/ralph"

case "$COMMAND" in
    plan)
        echo "=== Plan Mode ==="
        echo "Generating implementation plan for: $PROJECT"
        echo ""

        # Generate plan (reads specs/*.md, NOT scenarios/)
        python3 "$RALPH_BIN" plan

        echo ""
        echo "Review IMPLEMENTATION_PLAN.md before running build mode."
        echo "To proceed with build: ./loop.sh build --project $PROJECT"
        ;;

    scenarios)
        echo "=== Scenario Authorship Mode ==="
        echo "Generating scenarios for: $PROJECT"
        echo ""

        # Generate scenarios (reads specs/*.md, NOT IMPLEMENTATION_PLAN.md)
        python3 "$RALPH_BIN" scenarios

        echo ""
        echo "Review scenarios/*.yaml before running build."
        echo "Scenarios are protected from Ralph's access."
        ;;

    build)
        echo "=== Build Mode ==="
        echo "Running Ralph agent loop for: $PROJECT"
        echo ""

        # Run Ralph
        python3 "$RALPH_BIN" run --project "$PROJECT"
        ;;

    *)
        echo "Usage: loop.sh {plan|build|scenarios} --project <name>"
        exit 1
        ;;
esac
