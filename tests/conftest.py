"""Pytest configuration and shared fixtures for scenario loop tests."""

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_signal_path(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary path for signal file tests."""
    signal_path = tmp_path / "ralph-scenario-result.json"
    yield signal_path
    if signal_path.exists():
        signal_path.unlink()


@pytest.fixture
def temp_scenarios_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary scenarios directory."""
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    yield scenarios_dir
    if scenarios_dir.exists():
        for f in scenarios_dir.iterdir():
            f.unlink()
        scenarios_dir.rmdir()


@pytest.fixture
def temp_specs_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary specs directory."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    yield specs_dir
    if specs_dir.exists():
        for f in specs_dir.iterdir():
            f.unlink()
        specs_dir.rmdir()


@pytest.fixture
def sample_yaml_scenario() -> str:
    """Sample YAML scenario for testing."""
    return """name: test-scenario
trigger:
  type: http
  method: POST
  path: /api/checkout
  body:
    items:
      - sku-a
env:
  order_id: ord_123
assertions:
  - type: http_status
    path: /api/orders
    expect: 201
  - type: db_record
    table: orders
    conditions:
      id: ord_123
      status: pending
"""


@pytest.fixture
def sample_http_scenario() -> str:
    """Sample HTTP trigger scenario."""
    return """name: http-check
trigger:
  type: http
  method: GET
  path: /api/health
assertions:
  - type: http_status
    path: /api/health
    expect: 200
"""


@pytest.fixture
def sample_db_scenario() -> str:
    """Sample DB record scenario."""
    return """name: db-check
trigger:
  type: http
  method: POST
  path: /api/orders
  body:
    order_id: ord_456
assertions:
  - type: db_record
    table: orders
    conditions:
      id: ord_456
      status: pending
"""


@contextmanager
def mock_signal_path(temp_signal_path: Path):
    """Context manager to mock the global SIGNAL_PATH."""
    with patch("src.signal.SIGNAL_PATH", temp_signal_path):
        yield


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing assertions."""
    mock = MagicMock()
    mock.get.return_value = MagicMock(status_code=200)
    mock.post.return_value = MagicMock(status_code=201)
    return mock


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing assertions."""
    mock = MagicMock()
    first_mock = MagicMock()
    mock.query.return_value = MagicMock(first=MagicMock(return_value=first_mock))
    return mock


@pytest.fixture
def state_file_path(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary state file path."""
    state_path = tmp_path / "ralph-state.json"
    yield state_path
    if state_path.exists():
        state_path.unlink()
