"""Scenario author module for harness compatibility.

This module re-exports the scenario authoring functionality from src.scenario_author
for use by the harness package.
"""

from src.scenario_author import Scenario, load_scenarios, save_scenarios, Assertion

__all__ = ["Scenario", "load_scenarios", "save_scenarios", "Assertion"]