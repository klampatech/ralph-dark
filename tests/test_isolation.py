"""Tests for filesystem isolation - TC-01 from Section 3."""

import os
import stat
from pathlib import Path

import pytest


class TestFilesystemIsolation:
    """Tests for filesystem isolation (TC-01 from Section 3)."""

    def test_scenarios_directory_exists(self):
        """Scenarios directory exists."""
        scenarios_dir = Path(__file__).parent.parent / "scenarios"
        assert scenarios_dir.exists()

    def test_isolation_active_after_apply(self, tmp_path):
        """apply_isolation makes scenarios directory unreadable."""
        import harness.isolation as isolation

        # Create a temp scenarios dir
        test_dir = tmp_path / "scenarios"
        test_dir.mkdir()

        original_scenarios_dir = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = test_dir

        try:
            isolation.apply_isolation()

            # Directory should not be readable
            assert not os.access(test_dir, os.R_OK)
        finally:
            isolation.SCENARIOS_DIR = original_scenarios_dir

    def test_remove_isolation_restores_access(self, tmp_path):
        """remove_isolation restores read access."""
        import harness.isolation as isolation

        test_dir = tmp_path / "scenarios"
        test_dir.mkdir()

        original_scenarios_dir = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = test_dir

        try:
            isolation.apply_isolation()
            assert not os.access(test_dir, os.R_OK)

            isolation.remove_isolation()
            assert os.access(test_dir, os.R_OK)
        finally:
            isolation.SCENARIOS_DIR = original_scenarios_dir

    def test_is_isolation_active_detection(self, tmp_path):
        """is_isolation_active correctly detects isolation state."""
        import harness.isolation as isolation

        test_dir = tmp_path / "scenarios"
        test_dir.mkdir()

        original_scenarios_dir = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = test_dir

        try:
            # Initially no isolation
            assert isolation.is_isolation_active() is False

            # Apply isolation
            isolation.apply_isolation()
            assert isolation.is_isolation_active() is True

            # Remove isolation
            isolation.remove_isolation()
            assert isolation.is_isolation_active() is False
        finally:
            isolation.SCENARIOS_DIR = original_scenarios_dir

    def test_read_denied_when_isolated(self, tmp_path):
        """Read operations are denied when isolation is active."""
        import harness.isolation as isolation

        test_dir = tmp_path / "scenarios"
        test_dir.mkdir()
        test_file = test_dir / "test.yaml"
        test_file.write_text("name: test")

        original_scenarios_dir = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = test_dir

        try:
            isolation.apply_isolation()

            # Attempting to read should fail
            with pytest.raises(PermissionError):
                with open(test_file, 'r') as f:
                    f.read()
        finally:
            isolation.SCENARIOS_DIR = original_scenarios_dir
