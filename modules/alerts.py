"""
modules/alerts.py — SCMS Safety & Security Alerts Domain Module
================================================================
Handles classroom safety and security alerts (software simulation/prototype).

This is a DOMAIN module. It:
  - Queries SQLite via database.get_connection()
  - Enforces alert creation and resolution rules
  - Returns data as plain Python dictionaries/lists or (status, message) tuples
  - Contains NO input or print statements
  - Uses parameterized SQL queries exclusively

SIMULATION NOTE:
  This is a software simulation and demonstration prototype.
  There is NO connection to real-world sensors, hardware, CCTV,
  fire systems, or emergency services.

Architecture:
  main.py → role menu (student / teacher / admin)
              → alerts.py
                  → database.py → SQLite

Schema reference:
  - alerts (id, alert_type, location, description, status,
            created_by, created_at, resolved_by, resolved_at)
      alert_type: 'Fire', 'Unauthorized Access', 'Medical', 'Other'
      status: 'Active', 'Resolved'
      created_by, resolved_by reference users.id
"""

import sqlite3
from database import get_connection

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALERT_TYPES = (
    "Fire",
    "Unauthorized Access",
    "Medical",
    "Other",
)

ALERT_STATUSES = (
    "Active",
    "Resolved",
)


# ---------------------------------------------------------------------------
# Query functions (Read operations)
# ---------------------------------------------------------------------------

def get_alerts() -> list[dict]:
    """
    Return all alerts (both Active and Resolved), sorted newest first.

    Joins the users table to include creator and resolver names/usernames.

    Returns:
        List of dictionaries with alert details.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.alert_type,
                a.location,
                a.description,
                a.status,
                a.created_by,
                a.created_at,
                a.resolved_by,
                a.resolved_at,
                u1.name AS creator_name,
                u1.username AS creator_username,
                u2.name AS resolver_name,
                u2.username AS resolver_username
            FROM alerts a
            JOIN users u1 ON a.created_by = u1.id
            LEFT JOIN users u2 ON a.resolved_by = u2.id
            ORDER BY a.id DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_active_alerts() -> list[dict]:
    """
    Return only alerts where status = 'Active', sorted newest first.

    Returns:
        List of dictionaries representing active alerts.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.alert_type,
                a.location,
                a.description,
                a.status,
                a.created_by,
                a.created_at,
                a.resolved_by,
                a.resolved_at,
                u1.name AS creator_name,
                u1.username AS creator_username,
                u2.name AS resolver_name,
                u2.username AS resolver_username
            FROM alerts a
            JOIN users u1 ON a.created_by = u1.id
            LEFT JOIN users u2 ON a.resolved_by = u2.id
            WHERE a.status = 'Active'
            ORDER BY a.id DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_alert(alert_id: int) -> dict | None:
    """
    Fetch a single alert by its database ID.

    Parameters:
        alert_id — Integer primary key in the alerts table

    Returns:
        Dictionary representing the alert, or None if not found.
    """
    if not isinstance(alert_id, int):
        return None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.alert_type,
                a.location,
                a.description,
                a.status,
                a.created_by,
                a.created_at,
                a.resolved_by,
                a.resolved_at,
                u1.name AS creator_name,
                u1.username AS creator_username,
                u2.name AS resolver_name,
                u2.username AS resolver_username
            FROM alerts a
            JOIN users u1 ON a.created_by = u1.id
            LEFT JOIN users u2 ON a.resolved_by = u2.id
            WHERE a.id = ?
            """,
            (alert_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_alerts_by_status(status: str) -> list[dict]:
    """
    Return alerts matching a specific status ('Active' or 'Resolved'),
    sorted newest first.

    Parameters:
        status — 'Active' or 'Resolved'

    Returns:
        List of matching alert dictionaries, or empty list if status is invalid.
    """
    if status not in ALERT_STATUSES:
        return []

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                a.id,
                a.alert_type,
                a.location,
                a.description,
                a.status,
                a.created_by,
                a.created_at,
                a.resolved_by,
                a.resolved_at,
                u1.name AS creator_name,
                u1.username AS creator_username,
                u2.name AS resolver_name,
                u2.username AS resolver_username
            FROM alerts a
            JOIN users u1 ON a.created_by = u1.id
            LEFT JOIN users u2 ON a.resolved_by = u2.id
            WHERE a.status = ?
            ORDER BY a.id DESC
            """,
            (status,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_alert_history() -> list[dict]:
    """
    Return complete alert history (both Active and Resolved alerts).
    Delegates to get_alerts().
    """
    return get_alerts()


# ---------------------------------------------------------------------------
# Mutation operations (Create and Resolve)
# ---------------------------------------------------------------------------

def create_alert(
    alert_type: str,
    location: str,
    description: str,
    created_by: int
) -> tuple[bool, str]:
    """
    Create a new safety/security alert.

    Validation rules:
      1. alert_type must be in ALERT_TYPES.
      2. location must not be empty.
      3. description must not be empty.
      4. created_by must refer to an existing user in the users table.

    Database fields populated:
      - status = 'Active'
      - created_at = CURRENT_TIMESTAMP
      - resolved_by = NULL
      - resolved_at = NULL

    Parameters:
        alert_type  — 'Fire', 'Unauthorized Access', 'Medical', or 'Other'
        location    — Location string (e.g. "Room 101", "Computer Lab")
        description — Detailed incident description
        created_by  — Integer ID of the user reporting the alert (users.id)

    Returns:
        (True, "Alert created successfully.") on success,
        or (False, <error message>) on failure.
    """
    # 1. Validate alert_type
    if not alert_type or alert_type not in ALERT_TYPES:
        return False, f"Invalid alert type '{alert_type}'. Allowed types: {', '.join(ALERT_TYPES)}."

    # 2. Validate location
    if not location or not isinstance(location, str) or not location.strip():
        return False, "Location cannot be empty."
    clean_location = location.strip()

    # 3. Validate description
    if not description or not isinstance(description, str) or not description.strip():
        return False, "Description cannot be empty."
    clean_description = description.strip()

    # 4. Validate creator user ID
    if not isinstance(created_by, int):
        return False, "Invalid creator user ID."

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ?", (created_by,))
        if not cursor.fetchone():
            return False, f"User with ID {created_by} does not exist."

        # Insert new active alert
        cursor.execute(
            """
            INSERT INTO alerts
                (alert_type, location, description, status,
                 created_by, created_at, resolved_by, resolved_at)
            VALUES (?, ?, ?, 'Active', ?, CURRENT_TIMESTAMP, NULL, NULL)
            """,
            (alert_type, clean_location, clean_description, created_by)
        )
        conn.commit()
        return True, "Alert created successfully."

    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error while creating alert: {e}"
    finally:
        conn.close()


def resolve_alert(alert_id: int, resolved_by: int) -> tuple[bool, str]:
    """
    Resolve an active safety/security alert.

    Validation rules:
      1. Alert must exist.
      2. Alert must currently have status = 'Active'.
      3. If already resolved, reject with informative message.
      4. resolved_by must refer to an existing user in the users table.

    Updates:
      - status = 'Resolved'
      - resolved_by = resolved_by
      - resolved_at = CURRENT_TIMESTAMP

    Parameters:
        alert_id    — ID of the alert to resolve
        resolved_by — Integer ID of the resolving user (users.id)

    Returns:
        (True, "Alert resolved successfully.") on success,
        or (False, <error message>) on failure.
    """
    if not isinstance(alert_id, int):
        return False, "Alert not found."

    if not isinstance(resolved_by, int):
        return False, "Invalid resolver user ID."

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Step 1: Check if alert exists and check current status
        cursor.execute("SELECT id, status FROM alerts WHERE id = ?", (alert_id,))
        alert = cursor.fetchone()
        if not alert:
            return False, "Alert not found."

        if alert["status"] == "Resolved":
            return False, "Alert is already resolved."

        if alert["status"] != "Active":
            return False, f"Alert cannot be resolved (current status: {alert['status']})."

        # Step 2: Check if resolving user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (resolved_by,))
        if not cursor.fetchone():
            return False, f"User with ID {resolved_by} does not exist."

        # Step 3: Update alert to Resolved
        cursor.execute(
            """
            UPDATE alerts
            SET status = 'Resolved',
                resolved_by = ?,
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (resolved_by, alert_id)
        )
        conn.commit()
        return True, "Alert resolved successfully."

    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error while resolving alert: {e}"
    finally:
        conn.close()
