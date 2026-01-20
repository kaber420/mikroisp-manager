# app/db/audit_db.py
"""
Database module for audit log persistence and retrieval.
Stores security-relevant actions in SQLite for admin UI access.
"""

import json
import sqlite3

from .base import get_db_connection


def _ensure_audit_table(conn: sqlite3.Connection) -> None:
    """Creates the audit_logs table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            username TEXT NOT NULL,
            user_role TEXT,
            ip_address TEXT,
            status TEXT NOT NULL DEFAULT 'success',
            details TEXT
        )
    """)
    # Create indexes for common queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
        ON audit_logs(timestamp DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_action 
        ON audit_logs(action)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_username 
        ON audit_logs(username)
    """)
    conn.commit()


def get_audit_connection() -> sqlite3.Connection:
    """Returns a connection to the main inventory DB with audit table ensured."""
    conn = get_db_connection()
    _ensure_audit_table(conn)
    return conn


def save_audit_log(log_entry: dict) -> None:
    """
    Persists an audit log entry to SQLite.

    Args:
        log_entry: Dictionary with audit data (timestamp, action, resource_type, etc.)
    """
    conn = None
    try:
        conn = get_audit_connection()

        # Convert details dict to JSON string if present
        details_json = None
        if log_entry.get("details"):
            details_json = json.dumps(log_entry["details"], ensure_ascii=False)

        conn.execute(
            """
            INSERT INTO audit_logs 
            (timestamp, action, resource_type, resource_id, username, user_role, ip_address, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                log_entry.get("timestamp"),
                log_entry.get("action"),
                log_entry.get("resource_type"),
                log_entry.get("resource_id"),
                log_entry.get("user", "anonymous"),
                log_entry.get("user_role", "unknown"),
                log_entry.get("ip_address", "unknown"),
                log_entry.get("status", "success"),
                details_json,
            ),
        )
        conn.commit()
    except Exception as e:
        print(f"⚠️ Error saving audit log to DB: {e}")
    finally:
        if conn:
            conn.close()


def get_audit_logs_paginated(
    page: int = 1,
    page_size: int = 20,
    action_filter: str | None = None,
    username_filter: str | None = None,
) -> list[dict]:
    """
    Retrieves audit logs with pagination and optional filters.

    Args:
        page: Page number (1-indexed)
        page_size: Number of records per page
        action_filter: Filter by action type (DELETE, UPDATE, CREATE, etc.)
        username_filter: Filter by username

    Returns:
        List of audit log dictionaries
    """
    conn = None
    try:
        conn = get_audit_connection()
        offset = (page - 1) * page_size

        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if action_filter and action_filter != "all":
            query += " AND action = ?"
            params.append(action_filter.upper())

        if username_filter and username_filter != "all":
            query += " AND username = ?"
            params.append(username_filter)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        cursor = conn.execute(query, tuple(params))
        rows = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Parse details JSON back to dict
            if row_dict.get("details"):
                try:
                    row_dict["details"] = json.loads(row_dict["details"])
                except json.JSONDecodeError:
                    pass
            rows.append(row_dict)
        return rows

    except Exception as e:
        print(f"⚠️ Error reading audit logs: {e}")
        return []
    finally:
        if conn:
            conn.close()


def count_audit_logs(action_filter: str | None = None, username_filter: str | None = None) -> int:
    """
    Counts total audit logs matching the given filters.

    Args:
        action_filter: Filter by action type
        username_filter: Filter by username

    Returns:
        Total count of matching records
    """
    conn = None
    try:
        conn = get_audit_connection()

        query = "SELECT COUNT(*) FROM audit_logs WHERE 1=1"
        params = []

        if action_filter and action_filter != "all":
            query += " AND action = ?"
            params.append(action_filter.upper())

        if username_filter and username_filter != "all":
            query += " AND username = ?"
            params.append(username_filter)

        cursor = conn.execute(query, tuple(params))
        return cursor.fetchone()[0]

    except Exception as e:
        print(f"⚠️ Error counting audit logs: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def get_distinct_usernames() -> list[str]:
    """Returns a list of distinct usernames who have audit entries."""
    conn = None
    try:
        conn = get_audit_connection()
        cursor = conn.execute("SELECT DISTINCT username FROM audit_logs ORDER BY username")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"⚠️ Error getting usernames: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_distinct_actions() -> list[str]:
    """Returns a list of distinct action types in the audit log."""
    conn = None
    try:
        conn = get_audit_connection()
        cursor = conn.execute("SELECT DISTINCT action FROM audit_logs ORDER BY action")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"⚠️ Error getting actions: {e}")
        return []
    finally:
        if conn:
            conn.close()
