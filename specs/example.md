# Example Scenario Specification

This is an example spec used for testing the scenario harness.

## Scenario: health_check

### Assertions
- http_status:
    url: http://localhost:8000/health
    expected: 200
- db_record:
    query: SELECT 1
    expected_rows: 1

## Scenario: api_status

### Assertions
- http_status:
    url: http://localhost:8000/api/v1/status
    expected: 200