"""Tests for Plan Review Gate (TC-01 from Section 4).

These tests verify that:
- ./loop.sh plan --project myproject generates IMPLEMENTATION_PLAN.md
- The operator can review it before running build mode
- Build mode does not start until operator explicitly invokes it
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestPlanReviewGateTC01:
    """Tests for Plan Review Gate - TC-01 from Section 4."""

    def test_plan_generates_implementation_plan_file(self, tmp_path):
        """Plan command generates IMPLEMENTATION_PLAN.md file."""
        # Setup: Create temporary project structure
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        specs_dir.joinpath("test.md").write_text(
            "# Feature: Test Project\n\n"
            "## Scenario: Test scenario\n"
            "Given a test\nWhen a test\nThen a test\n"
        )

        # Execute: Run plan command
        loop_sh = Path(__file__).parent.parent / "loop.sh"
        os.chmod(loop_sh, 0o755)

        result = subprocess.run(
            [str(loop_sh), "plan", "--project", "TestProject"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # Verify: IMPLEMENTATION_PLAN.md is created
        impl_plan = tmp_path / "IMPLEMENTATION_PLAN.md"
        assert impl_plan.exists(), f"Expected IMPLEMENTATION_PLAN.md to exist. stderr: {result.stderr}"
        assert result.returncode == 0, f"Expected return code 0, got {result.returncode}. stderr: {result.stderr}"

    def test_plan_file_contains_project_name(self, tmp_path):
        """Generated IMPLEMENTATION_PLAN.md contains the project name."""
        project_name = "MyAwesomeProject"

        # Setup
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        specs_dir.joinpath("test.md").write_text(
            f"# Feature: {project_name}\n\n"
            "## Scenario: Test scenario\n"
            "Given a test\nWhen a test\nThen a test\n"
        )

        # Execute
        loop_sh = Path(__file__).parent.parent / "loop.sh"
        os.chmod(loop_sh, 0o755)

        subprocess.run(
            [str(loop_sh), "plan", "--project", project_name],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # Verify: File contains project name in header
        impl_plan = tmp_path / "IMPLEMENTATION_PLAN.md"
        content = impl_plan.read_text()
        assert f"# Implementation Plan: {project_name}" in content

    def test_plan_file_contains_tasks_from_specs(self, tmp_path):
        """Generated IMPLEMENTATION_PLAN.md contains tasks from specs/*.md."""
        # Setup
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        specs_dir.joinpath("api.md").write_text(
            "# Feature: API Feature\n\n"
            "## Scenario: API status check\n"
            "Given the API is running\nWhen checking status\nThen return 200\n"
        )
        specs_dir.joinpath("db.md").write_text(
            "# Feature: DB Feature\n\n"
            "## Scenario: DB connection check\n"
            "Given the DB is running\nWhen checking connection\nThen return connected\n"
        )

        # Execute
        loop_sh = Path(__file__).parent.parent / "loop.sh"
        os.chmod(loop_sh, 0o755)

        subprocess.run(
            [str(loop_sh), "plan", "--project", "TestProject"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # Verify: Tasks from both spec files are included
        impl_plan = tmp_path / "IMPLEMENTATION_PLAN.md"
        content = impl_plan.read_text()
        assert "API status check" in content or "API status" in content
        assert "DB connection check" in content or "DB connection" in content

    def test_plan_shows_review_gate_message(self, tmp_path):
        """Plan command shows review gate message to operator."""
        # Setup
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        specs_dir.joinpath("test.md").write_text(
            "# Feature: Test\n\n## Scenario: Test\nGiven test\nWhen test\nThen test\n"
        )

        # Execute
        loop_sh = Path(__file__).parent.parent / "loop.sh"
        os.chmod(loop_sh, 0o755)

        result = subprocess.run(
            [str(loop_sh), "plan", "--project", "TestProject"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # Verify: Review gate message is shown
        output = result.stdout + result.stderr
        assert "review" in output.lower() or "gate" in output.lower(), \
            f"Expected review gate message in output. Got: {output}"

    def test_plan_does_not_start_build_mode(self, tmp_path):
        """Plan command does not automatically start build mode."""
        # Setup
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        specs_dir.joinpath("test.md").write_text(
            "# Feature: Test\n\n## Scenario: Test\nGiven test\nWhen test\nThen test\n"
        )

        # Execute
        loop_sh = Path(__file__).parent.parent / "loop.sh"
        os.chmod(loop_sh, 0o755)

        result = subprocess.run(
            [str(loop_sh), "plan", "--project", "TestProject"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # Verify: Build mode is NOT started (no "Building" or "Ralph agent" messages)
        output = result.stdout + result.stderr
        assert "Ralph agent loop" not in output, \
            f"Build mode should not start automatically. Got: {output}"
        assert "Build mode:" not in output or "waits for" in output, \
            f"Build mode should not auto-start. Got: {output}"

    def test_build_mode_requires_explicit_invocation(self, tmp_path):
        """Build mode requires explicit operator invocation."""
        loop_sh = Path(__file__).parent.parent / "loop.sh"
        os.chmod(loop_sh, 0o755)

        # Execute: Try to run build mode without plan
        result = subprocess.run(
            [str(loop_sh), "build"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # Verify: Either error (plan not found) or waits for explicit invocation
        output = result.stdout + result.stderr
        if result.returncode != 0:
            assert "IMPLEMENTATION_PLAN" in output or "not found" in output.lower()
        else:
            # If it succeeds, it should indicate waiting for invocation
            assert "operator" in output.lower() or "invocation" in output.lower() or "explicit" in output.lower()

    def test_plan_generates_valid_markdown(self, tmp_path):
        """Generated IMPLEMENTATION_PLAN.md is valid markdown."""
        # Setup
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        specs_dir.joinpath("test.md").write_text(
            "# Feature: Test Feature\n\n"
            "## Scenario: Test scenario\n"
            "Given a condition\nWhen an action\nThen a result\n"
        )

        # Execute
        loop_sh = Path(__file__).parent.parent / "loop.sh"
        os.chmod(loop_sh, 0o755)

        subprocess.run(
            [str(loop_sh), "plan", "--project", "TestProject"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # Verify: Valid markdown structure
        impl_plan = tmp_path / "IMPLEMENTATION_PLAN.md"
        content = impl_plan.read_text()
        # Should have markdown header
        assert content.startswith("#")
        # Should have tasks section
        assert "## Tasks" in content or "Tasks" in content
        # Should have task items with checkboxes
        assert "[ ]" in content or "[x]" in content


class TestPlanCommandIntegration:
    """Integration tests for plan command with full workflow."""

    def test_full_plan_workflow(self, tmp_path):
        """Complete workflow: create specs -> run plan -> review -> build."""
        # Step 1: Create specs
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        specs_dir.joinpath("feature-a.md").write_text(
            "# Feature: Feature A\n\n"
            "## Scenario: Feature A scenario\n"
            "Given Feature A is needed\nWhen implementing\nThen Feature A works\n"
        )

        # Step 2: Run plan
        loop_sh = Path(__file__).parent.parent / "loop.sh"
        os.chmod(loop_sh, 0o755)

        plan_result = subprocess.run(
            [str(loop_sh), "plan", "--project", "MyProject"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )
        assert plan_result.returncode == 0

        # Step 3: Verify plan exists and has content
        impl_plan = tmp_path / "IMPLEMENTATION_PLAN.md"
        assert impl_plan.exists()
        content = impl_plan.read_text()
        assert "# Implementation Plan: MyProject" in content
        assert "Feature A" in content

        # Step 4: Build mode should still wait for invocation
        build_result = subprocess.run(
            [str(loop_sh), "build"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )
        # Build should indicate waiting for operator invocation
        # The placeholder text is OK as long as it mentions waiting/explicit/invocation
        build_output = build_result.stdout + build_result.stderr
        # Check that it explicitly says it's waiting (not auto-running)
        assert any(word in build_output.lower() for word in ["waits", "operator", "invocation", "explicit"]), \
            f"Expected build mode to indicate waiting for invocation. Got: {build_output}"

    def test_multiple_specs_merged_correctly(self, tmp_path):
        """Multiple spec files are merged into single plan."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()

        # Create multiple spec files
        for i in range(1, 4):
            specs_dir.joinpath(f"feature-{i}.md").write_text(
                f"# Feature: Feature {i}\n\n"
                f"## Scenario: Feature {i} scenario\n"
                f"Given feature {i}\nWhen implementing\nThen feature {i} works\n"
            )

        # Run plan
        loop_sh = Path(__file__).parent.parent / "loop.sh"
        os.chmod(loop_sh, 0o755)

        subprocess.run(
            [str(loop_sh), "plan", "--project", "MultiFeature"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # Verify: All features are in the plan
        impl_plan = tmp_path / "IMPLEMENTATION_PLAN.md"
        content = impl_plan.read_text()
        assert "Feature 1" in content
        assert "Feature 2" in content
        assert "Feature 3" in content
