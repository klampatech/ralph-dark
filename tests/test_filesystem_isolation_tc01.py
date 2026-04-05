"""Tests for TC-01: Filesystem isolation - Ralph cannot read scenarios/.

Scenario: Filesystem isolation (TC-01 from Section 3)
Given Ralph is running in ~/gt/projects/myproject/
When Ralph attempts to read any file in scenarios/
Then the read operation is denied by OS-level permissions
And Ralph cannot determine whether scenarios exist

These tests verify that:
1. SCENARIOS_DIR is configurable based on project root
2. apply_isolation() denies read access to the scenarios directory
3. File read operations are denied when isolation is active
"""

import os
import stat
from pathlib import Path

import pytest


class TestFilesystemIsolationTC01:
    """Tests for TC-01 Filesystem Isolation scenario."""

    def test_scenarios_dir_is_configurable(self, tmp_path):
        """SCENARIOS_DIR should be configurable based on project path."""
        import harness.isolation as isolation

        project_root = tmp_path / "myproject"
        project_root.mkdir()

        # Mock the SCENARIOS_DIR to use project root
        scenarios_dir = project_root / "scenarios"
        scenarios_dir.mkdir()

        original = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = scenarios_dir

        try:
            isolation.apply_isolation()

            # Directory should not be readable
            assert not os.access(scenarios_dir, os.R_OK)
        finally:
            isolation.SCENARIOS_DIR = original
            # Restore permissions for cleanup
            if scenarios_dir.exists():
                os.chmod(scenarios_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def test_read_denied_when_isolated(self, tmp_path):
        """Read operations are denied when isolation is active."""
        import harness.isolation as isolation

        project_root = tmp_path / "myproject"
        project_root.mkdir()

        scenarios_dir = project_root / "scenarios"
        scenarios_dir.mkdir()

        test_file = scenarios_dir / "test.yaml"
        test_file.write_text("name: test")

        original = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = scenarios_dir

        try:
            isolation.apply_isolation()

            # Attempting to read should fail with PermissionError
            with pytest.raises(PermissionError):
                with open(test_file, 'r') as f:
                    f.read()
        finally:
            isolation.SCENARIOS_DIR = original
            if scenarios_dir.exists():
                os.chmod(scenarios_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def test_open_denied_when_isolated(self, tmp_path):
        """open() is denied when isolation is active."""
        import harness.isolation as isolation

        project_root = tmp_path / "myproject"
        project_root.mkdir()

        scenarios_dir = project_root / "scenarios"
        scenarios_dir.mkdir()

        test_file = scenarios_dir / "scenario.yaml"
        test_file.write_text("name: test")

        original = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = scenarios_dir

        try:
            isolation.apply_isolation()

            # open() should raise PermissionError
            with pytest.raises(PermissionError):
                open(test_file, 'r')
        finally:
            isolation.SCENARIOS_DIR = original
            if scenarios_dir.exists():
                os.chmod(scenarios_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def test_glob_denied_when_isolated(self, tmp_path):
        """glob.glob() returns empty when isolation is active - Ralph cannot list scenarios."""
        import harness.isolation as isolation

        project_root = tmp_path / "myproject"
        project_root.mkdir()

        scenarios_dir = project_root / "scenarios"
        scenarios_dir.mkdir()

        # Create some scenario files
        (scenarios_dir / "scenario_1.yaml").write_text("name: s1")
        (scenarios_dir / "scenario_2.yaml").write_text("name: s2")

        original = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = scenarios_dir

        try:
            isolation.apply_isolation()

            # glob.glob should return empty when directory is unreadable
            # (cannot read directory contents)
            import glob
            results = glob.glob(str(scenarios_dir / "*.yaml"))
            assert len(results) == 0, "glob should return empty when directory is not readable"
        finally:
            isolation.SCENARIOS_DIR = original
            if scenarios_dir.exists():
                os.chmod(scenarios_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def test_isolation_works_from_different_cwd(self, tmp_path):
        """Isolation works regardless of current working directory."""
        import harness.isolation as isolation

        # Create project in one location
        project_root = tmp_path / "myproject"
        project_root.mkdir()

        scenarios_dir = project_root / "scenarios"
        scenarios_dir.mkdir()

        test_file = scenarios_dir / "test.yaml"
        test_file.write_text("test content")

        original = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = scenarios_dir

        try:
            isolation.apply_isolation()

            # Change to different directory
            old_cwd = os.getcwd()
            other_dir = tmp_path / "other"
            other_dir.mkdir()
            try:
                os.chdir(other_dir)
                # Should still be denied even from different cwd
                with pytest.raises(PermissionError):
                    with open(scenarios_dir / "test.yaml", 'r') as f:
                        f.read()
            finally:
                os.chdir(old_cwd)
        finally:
            isolation.SCENARIOS_DIR = original
            if scenarios_dir.exists():
                os.chmod(scenarios_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def test_scandir_denied_when_isolated(self, tmp_path):
        """Path.iterdir() fails when isolation is active."""
        import harness.isolation as isolation

        project_root = tmp_path / "myproject"
        project_root.mkdir()

        scenarios_dir = project_root / "scenarios"
        scenarios_dir.mkdir()

        # Create some scenario files
        (scenarios_dir / "scenario.yaml").write_text("name: test")

        original = isolation.SCENARIOS_DIR
        isolation.SCENARIOS_DIR = scenarios_dir

        try:
            isolation.apply_isolation()

            # iterdir() should raise PermissionError when directory is unreadable
            with pytest.raises(PermissionError):
                list(scenarios_dir.iterdir())
        finally:
            isolation.SCENARIOS_DIR = original
            if scenarios_dir.exists():
                os.chmod(scenarios_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
