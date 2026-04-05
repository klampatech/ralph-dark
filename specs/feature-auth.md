# Feature: User Authentication System

## Scenario: Valid login returns 200
Given a running system at http://localhost:8080
When POST /api/login {"username": "alice", "password": "secret123"}
Then the response status is 201

## Scenario: Invalid login returns 401
Given a running system at http://localhost:8080
When POST /api/login {"username": "alice", "password": "wrong"}
Then the response status is 401

## Scenario: User record exists in database
Given a running system with database accessible to harness
And env: { "user_id": "usr_123" }
When the scenario executes
Then the harness queries the users table for id=usr_123
And asserts the record exists with status=active
