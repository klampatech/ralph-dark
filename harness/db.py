"""Database assertion support for scenario harness."""

from __future__ import annotations

import json
from typing import Any


def execute_query(query: str) -> dict[str, Any]:
    """Execute a database query and return result.

    Args:
        query: SQL query to execute.

    Returns:
        Dict with 'success', 'row_count', and optionally 'error'.
    """
    try:
        import sqlite3

        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return {"success": True, "row_count": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def assert_db_record(query: str, expected_rows: int | None = None) -> bool:
    """Assert database record conditions.

    Args:
        query: SQL query to execute.
        expected_rows: Optional expected row count.

    Returns:
        True if assertion passes, False otherwise.
    """
    result = execute_query(query)

    if not result.get("success"):
        return False

    if expected_rows is not None:
        return result.get("row_count", 0) == expected_rows

    return result.get("row_count", 0) > 0