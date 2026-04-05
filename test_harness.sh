#!/bin/bash
# Test script for Ralph Dark Harness

set -e

SIGNAL_FILE="/tmp/ralph-scenario-result.json"
TEST_DIR="/tmp/ralph-harness-test"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR/scenarios"

echo "=== Test 1: No scenarios - should pass ==="
bash .orch/harness.sh "$TEST_DIR/scenarios" "$SIGNAL_FILE"
result=$(cat "$SIGNAL_FILE")
if [[ "$result" == '{"pass": true}' ]]; then
    echo "PASS: No scenarios returns pass=true"
else
    echo "FAIL: Expected {\"pass\": true}, got $result"
    exit 1
fi

echo ""
echo "=== Test 2: Failing HTTP assertion returns pass=false ==="
# When server is not running, curl returns "000" status
# If we expect 200, it should fail
cat > "$TEST_DIR/scenarios/fail_scenario.yaml" << 'EOF'
name: fail-scenario
trigger:
  type: http
  method: GET
  path: /health
assertions:
  - type: http_status
    expect: 200
EOF
bash .orch/harness.sh "$TEST_DIR/scenarios" "$SIGNAL_FILE"
result=$(cat "$SIGNAL_FILE")
if [[ "$result" == '{"pass": false}' ]]; then
    echo "PASS: Fail scenario returns pass=false"
else
    echo "FAIL: Expected {\"pass\": false}, got $result"
    exit 1
fi

echo ""
echo "=== Test 3: Signal file format is valid JSON ==="
if python3 -c "import json; json.loads('$(cat $SIGNAL_FILE)')" 2>/dev/null; then
    echo "PASS: Signal file is valid JSON"
else
    echo "FAIL: Signal file is not valid JSON"
    exit 1
fi

echo ""
echo "=== Test 4: Signal contains only pass boolean (no leaky data) ==="
# Parse the JSON and check it only has 'pass' key
if python3 -c "
import json
d = json.loads('$(cat $SIGNAL_FILE)')
if list(d.keys()) == ['pass'] and isinstance(d['pass'], bool):
    pass
else:
    raise ValueError('Invalid signal format')
" 2>/dev/null; then
    echo "PASS: Signal contains only 'pass' boolean field"
else
    echo "FAIL: Signal has extra fields or wrong format"
    exit 1
fi

echo ""
echo "=== Test 5: Post-commit hook exists and is executable ==="
if [[ -x .git/hooks/post-commit ]]; then
    echo "PASS: Post-commit hook exists and is executable"
else
    echo "FAIL: Post-commit hook not found or not executable"
    exit 1
fi

echo ""
echo "=== Test 6: Harness script exists and is executable ==="
if [[ -x .orch/harness.sh ]]; then
    echo "PASS: Harness script exists and is executable"
else
    echo "FAIL: Harness script not found or not executable"
    exit 1
fi

echo ""
echo "=== Test 7: Post-commit hook triggers harness ==="
# Create a scenario that will fail (server not running)
cat > "$TEST_DIR/scenarios/test.yaml" << 'EOF'
name: test
trigger:
  type: http
  method: GET
  path: /health
assertions:
  - type: http_status
    expect: 200
EOF
# Simulate post-commit by directly calling the hook
bash .git/hooks/post-commit
result=$(cat "$SIGNAL_FILE")
if [[ "$result" == '{"pass": false}' ]]; then
    echo "PASS: Post-commit hook triggers harness correctly"
else
    echo "FAIL: Post-commit hook did not trigger harness"
    exit 1
fi

echo ""
echo "=== All tests passed! ==="
rm -rf "$TEST_DIR"
