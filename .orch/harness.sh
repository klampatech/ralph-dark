#!/bin/bash
# Ralph Dark Factory Scenario Harness
# Reads scenarios/*.yaml and executes them against the running system
# Writes { "pass": true | false } to the signal file

set -e

SCENARIOS_DIR="${1:-scenarios}"
SIGNAL_FILE="${2:-/tmp/ralph-scenario-result.json}"

# Ensure signal file starts with pass:true as default
PASS=true

# Check if yq is available for parsing YAML
YQ_CMD=""
if command -v yq &> /dev/null; then
    YQ_CMD="yq"
elif command -v python3 &> /dev/null; then
    YQ_CMD="python3"
else
    echo "Warning: Neither yq nor python3 available, using basic YAML parsing" >&2
fi

# Function to execute a single assertion
execute_assertion() {
    local type="$1"
    local expect="$2"
    local actual="$3"
    
    if [[ "$type" == "equals" ]]; then
        if [[ "$actual" == "$expect" ]]; then
            return 0
        else
            return 1
        fi
    fi
    return 0
}

# Function to run a scenario
run_scenario() {
    local scenario_file="$1"
    local scenario_name
    local trigger_type
    local trigger_path
    local trigger_method
    local trigger_body
    local assertions
    
    if [[ -n "$YQ_CMD" ]]; then
        if [[ "$YQ_CMD" == "yq" ]]; then
            scenario_name=$(yq '.name' "$scenario_file" 2>/dev/null || echo "unnamed")
            trigger_type=$(yq '.trigger.type' "$scenario_file" 2>/dev/null || echo "")
            trigger_path=$(yq '.trigger.path' "$scenario_file" 2>/dev/null || echo "")
            trigger_method=$(yq '.trigger.method' "$scenario_file" 2>/dev/null || echo "GET")
            trigger_body=$(yq -ojson '.trigger.body' "$scenario_file" 2>/dev/null || echo "{}")
        else
            scenario_name=$(python3 -c "import yaml; d=yaml.safe_load(open('$scenario_file')); print(d.get('name','unnamed'))" 2>/dev/null || echo "unnamed")
            trigger_type=$(python3 -c "import yaml; d=yaml.safe_load(open('$scenario_file')); print(d.get('trigger',{}).get('type',''))" 2>/dev/null || echo "")
            trigger_path=$(python3 -c "import yaml; d=yaml.safe_load(open('$scenario_file')); print(d.get('trigger',{}).get('path',''))" 2>/dev/null || echo "")
            trigger_method=$(python3 -c "import yaml; d=yaml.safe_load(open('$scenario_file')); print(d.get('trigger',{}).get('method','GET'))" 2>/dev/null || echo "GET")
            trigger_body=$(python3 -c "import yaml,json; d=yaml.safe_load(open('$scenario_file')); print(json.dumps(d.get('trigger',{}).get('body',{})))" 2>/dev/null || echo "{}")
        fi
    else
        scenario_name="scenario"
        trigger_type="http_status"
        trigger_path="/"
        trigger_method="GET"
        trigger_body="{}"
    fi
    
    echo "Running scenario: $scenario_name"
    
    # Execute trigger if it's an HTTP request
    local http_result=""
    if [[ "$trigger_type" == "http" ]] || [[ -n "$trigger_path" ]]; then
        local url="http://localhost:8080$trigger_path"
        local response
        local status_code
        
        if [[ "$trigger_method" == "GET" ]]; then
            response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo -e "\n000")
        elif [[ "$trigger_method" == "POST" ]]; then
            response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$trigger_body" "$url" 2>/dev/null || echo -e "\n000")
        elif [[ "$trigger_method" == "PUT" ]]; then
            response=$(curl -s -w "\n%{http_code}" -X PUT -H "Content-Type: application/json" -d "$trigger_body" "$url" 2>/dev/null || echo -e "\n000")
        elif [[ "$trigger_method" == "DELETE" ]]; then
            response=$(curl -s -w "\n%{http_code}" -X DELETE "$url" 2>/dev/null || echo -e "\n000")
        fi
        
        http_result=$(echo "$response" | tail -1)
        http_body=$(echo "$response" | sed '$d')
    fi
    
    # Parse and execute assertions
    if [[ -n "$YQ_CMD" ]]; then
        # Check if scenario has assertions
        local has_assertions
        if [[ "$YQ_CMD" == "yq" ]]; then
            has_assertions=$(yq '.assertions | length > 0' "$scenario_file" 2>/dev/null || echo "false")
        else
            has_assertions=$(python3 -c "import yaml; d=yaml.safe_load(open('$scenario_file')); print(bool(d.get('assertions',[])))" 2>/dev/null || echo "false")
        fi
        
        # Only execute assertions if there are any defined
        if [[ "$has_assertions" == "true" ]] || [[ "$has_assertions" == "True" ]]; then
            if [[ "$trigger_type" == "http" ]] || [[ -n "$trigger_path" ]]; then
                local expect_status
                if [[ "$YQ_CMD" == "yq" ]]; then
                    expect_status=$(yq '.assertions[0].expect' "$scenario_file" 2>/dev/null || echo "200")
                else
                    expect_status=$(python3 -c "import yaml; d=yaml.safe_load(open('$scenario_file')); print(d.get('assertions',[{}])[0].get('expect',200))" 2>/dev/null || echo "200")
                fi
                
                if [[ "$http_result" == "$expect_status" ]]; then
                    echo "  Assertion passed: HTTP status $http_result == $expect_status"
                else
                    echo "  Assertion failed: HTTP status $http_result != $expect_status"
                    PASS=false
                fi
            fi
        else
            echo "  No assertions defined, scenario passes by default"
        fi
    else
        # Fallback: just check if server is reachable
        if curl -s --connect-timeout 2 http://localhost:8080 > /dev/null 2>&1; then
            echo "  Server reachable at localhost:8080"
        else
            echo "  Server not reachable"
            PASS=false
        fi
    fi
}

# Main execution
echo "Ralph Dark Harness: Reading scenarios from $SCENARIOS_DIR"

if [[ ! -d "$SCENARIOS_DIR" ]]; then
    echo "Scenarios directory not found: $SCENARIOS_DIR"
    echo '{"pass": false}' > "$SIGNAL_FILE"
    exit 1
fi

scenario_files=()
while IFS= read -r -d '' file; do
    scenario_files+=("$file")
done < <(find "$SCENARIOS_DIR" -maxdepth 1 -name "*.yaml" -print0 2>/dev/null | sort -z)

if [[ ${#scenario_files[@]} -eq 0 ]]; then
    echo "No scenario files found in $SCENARIOS_DIR"
    echo '{"pass": true}' > "$SIGNAL_FILE"
    exit 0
fi

echo "Found ${#scenario_files[@]} scenario(s)"

for scenario_file in "${scenario_files[@]}"; do
    run_scenario "$scenario_file" || PASS=false
done

# Write signal file
if [[ "$PASS" == "true" ]]; then
    echo '{"pass": true}' > "$SIGNAL_FILE"
else
    echo '{"pass": false}' > "$SIGNAL_FILE"
fi

echo "Signal written to $SIGNAL_FILE: $(cat "$SIGNAL_FILE")"
