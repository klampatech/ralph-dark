# Feature: Ralph Dark Factory Hidden Scenario Loop

## Scenario: Spec-driven parallel derivation (TC-01)
Given specs exist at specs/*.md
When plan mode and scenario authorship are triggered
Then IMPLEMENTATION_PLAN.md is generated without reading scenarios/
And scenarios/*.yaml is generated without reading IMPLEMENTATION_PLAN.md
And neither output references the other

## Scenario: Post-commit scenario execution (TC-02)
Given a commit is pushed to the repository
When the post-commit hook fires
Then the harness reads scenarios/*.yaml
And executes them against the running system
And writes { "pass": true | false } to /tmp/ralph-scenario-result.json
And Ralph reads the signal before the next iteration begins

## Scenario: Filesystem isolation (TC-01 from Section 3)
Given Ralph is running in ~/gt/projects/myproject/
When Ralph attempts to read any file in scenarios/
Then the read operation is denied by OS-level permissions
And Ralph cannot determine whether scenarios exist

## Scenario: Signal content (TC-02 from Section 3)
Given harness has executed all scenarios
When the signal file is written to /tmp/ralph-scenario-result.json
Then the file contains only valid JSON with a single "pass" boolean field
And no scenario names, error messages, or failure details are present

## Scenario: Leaky signal prevention (TC-03 from Section 3)
Given a scenario fails during harness execution
When /tmp/ralph-scenario-result.json is written
Then Ralph sees only { "pass": false }
And cannot infer which scenario failed, what was tested, or what error occurred

## Scenario: Plan review gate (TC-01 from Section 4)
Given specs exist at specs/*.md
When the operator runs ./loop.sh plan --project myproject
Then IMPLEMENTATION_PLAN.md is generated
And the operator can review it before running build mode
And build mode does not start until operator explicitly invokes it

## Scenario: Scenario review gate (TC-02 from Section 4)
Given specs exist at specs/*.md
When the operator runs scenario authorship
Then scenarios/*.yaml is generated
And the operator can review and approve before build mode
And build mode does not have access to unapproved scenarios

## Scenario: Spinning signal (TC-03 from Section 4)
Given Ralph is retrying the same task repeatedly
When the retry count exceeds the spinning threshold (default: 5)
Then /tmp/ralph-scenario-result.json contains { "spinning": true, "task": "task-name" }
And the operator is notified to intervene

## Scenario: Clean completion signal (TC-04 from Section 4)
Given all tasks in IMPLEMENTATION_PLAN.md are marked done
When the final scenario pass signal is received
Then /tmp/ralph-scenario-result.json contains { "done": true }
And the loop terminates cleanly

## Scenario: HTTP status assertion (TC-01 from Section 5)
Given a running system at http://localhost:8080
And a scenario with trigger: POST /api/checkout { items: [sku-a] }
And assertions: [ { "type": "http_status", "path": "/api/orders", "expect": 201 } ]
When the harness executes the scenario
Then the harness POSTs to /api/checkout
And asserts the response status is 201
And the signal reflects pass/fail correctly

## Scenario: DB record assertion (TC-02 from Section 5)
Given a running system with database accessible to harness
And a scenario with env: { "order_id": "ord_123" }
And assertions: [ { "type": "db_record", "table": "orders", "conditions": { "id": "ord_123", "status": "pending" } } ]
When the harness executes the scenario
Then the harness queries the orders table for id=ord_123
And asserts the record exists with status=pending

## Scenario: All-pass aggregation (TC-03 from Section 5)
Given 5 scenarios execute
And scenarios 1-4 assertions pass
And scenario 5 assertions pass
When harness writes signal
Then signal is { "pass": true }

## Scenario: Any-fail aggregation (TC-04 from Section 5)
Given 5 scenarios execute
And scenarios 1-4 assertions pass
And scenario 5 assertions fail
When harness writes signal
Then signal is { "pass": false }

## Scenario: Valid pass signal (TC-01 from Section 6)
Given harness executed with all scenarios passing
When harness writes the signal file
Then /tmp/ralph-scenario-result.json contains exactly { "pass": true }

## Scenario: Valid fail signal (TC-02 from Section 6)
Given harness executed with at least one scenario failing
When harness writes the signal file
Then /tmp/ralph-scenario-result.json contains exactly { "pass": false }

## Scenario: Malformed signal handling (TC-03 from Section 6)
Given harness encounters an error and cannot complete
When harness writes the signal file (or fails to write)
Then Ralph treats missing or malformed signal as { "pass": false }
And the loop retries the current task

## Scenario: Task advancement on pass (TC-01 from Section 7)
Given Ralph is on task N
And scenario signal is { "pass": true }
When Ralph processes the signal
Then task N is marked done in IMPLEMENTATION_PLAN.md
And Ralph picks task N+1 for the next iteration

## Scenario: Task retry on fail (TC-02 from Section 7)
Given Ralph is on task N
And scenario signal is { "pass": false }
When Ralph processes the signal
Then Ralph retries task N with fresh context
And retry count for task N is incremented

## Scenario: Spinning detection (TC-03 from Section 7)
Given Ralph has retried task N 5 times
And each time scenario signal was { "pass": false }
When Ralph processes the 5th failure signal
Then Ralph writes { "spinning": true, "task": "task-N-description" }
And the operator is notified to intervene

## Scenario: Retry count persistence (TC-04 from Section 7)
Given Ralph retried task N 3 times (all failed)
When the loop restarts (Ralph process exits and restarts)
Then retry count for task N is still 3
And spinning detection continues from count 3
