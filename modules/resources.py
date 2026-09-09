"""
modules/resources.py — SCMS Resource Management Domain Module
==============================================================
Handles classroom resource inventory, booking, returns, and maintenance.

This is a DOMAIN module. It:
  - Queries SQLite via database.get_connection()
  - Enforces booking rules, return rules, and maintenance rules
  - Executes multi-step updates inside SQLite transactions
  - Returns data as plain Python dictionaries/lists or (status, message) tuples
  - Contains NO input or print calls
  - Uses parameterized SQL queries exclusively

Architecture:
  main.py → role menu (student / teacher / admin)
              → resources.py
                  → database.py → SQLite

Schema reference:
  - resources (id, resource_code, name, status, maintenance_notes)
      status: 'Available', 'In Use', 'Maintenance'
  - bookings (id, resource_id, booked_by, booked_at, returned_at)
      booked_by references users.id directly
      returned_at IS NULL means the booking is currently active
"""

import sqlite3
from database import get_connection


# ---------------------------------------------------------------------------
# Query functions (Read operations)
# ---------------------------------------------------------------------------

def get_resources() -> list[dict]:
    """
    Return all classroom resources sorted by resource_code.

    Returns:
        List of dictionaries with keys:
        - id
        - resource_code
        - name
        - status
        - maintenance_notes
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, resource_code, name, status, maintenance_notes
            FROM resources
            ORDER BY resource_code
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_available_resources() -> list[dict]:
    """
    Return all classroom resources whose current status is 'Available',
    sorted by resource_code.

    Returns:
        List of dictionaries with keys:
        - id
        - resource_code
        - name
        - status
        - maintenance_notes
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, resource_code, name, status, maintenance_notes
            FROM resources
            WHERE status = 'Available'
            ORDER BY resource_code
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_resource(resource_id: int) -> dict | None:
    """
    Fetch a single resource by its internal database ID.

    Parameters:
        resource_id — Integer primary key in the resources table

    Returns:
        Dictionary representing the resource row, or None if not found.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, resource_code, name, status, maintenance_notes
            FROM resources
            WHERE id = ?
            """,
            (resource_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_resource_by_code(resource_code: str) -> dict | None:
    """
    Fetch a single resource by its unique user-facing resource_code.

    Strips surrounding whitespace and performs an exact match.

    Parameters:
        resource_code — String code (e.g. "R01", "R001")

    Returns:
        Dictionary representing the resource row, or None if not found.
    """
    if not resource_code or not isinstance(resource_code, str):
        return None

    cleaned_code = resource_code.strip()
    if not cleaned_code:
        return None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, resource_code, name, status, maintenance_notes
            FROM resources
            WHERE resource_code = ?
            """,
            (cleaned_code,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_active_booking(resource_id: int) -> dict | None:
    """
    Fetch the currently active booking for a resource (where returned_at is NULL).

    Parameters:
        resource_id — Integer primary key in the resources table

    Returns:
        Dictionary representing the active booking row, or None if none active.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, resource_id, booked_by, booked_at, returned_at
            FROM bookings
            WHERE resource_id = ? AND returned_at IS NULL
            """,
            (resource_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Booking and Return operations (Transactions)
# ---------------------------------------------------------------------------

def book_resource(resource_id: int, user_id: int) -> tuple[bool, str]:
    """
    Book an available resource for a user.

    Rules enforced:
      1. Resource must exist.
      2. Resource must currently have status 'Available'.
      3. User must exist.
      4. Inserts a new row into `bookings` with booked_at = CURRENT_TIMESTAMP
         and returned_at = NULL.
      5. Updates resource status to 'In Use'.
      6. Executed inside a database transaction (atomicity).

    Parameters:
        resource_id — ID of the resource to book
        user_id     — ID of the user booking the resource (users.id)

    Returns:
        (True, "Resource booked successfully.") on success,
        or (False, <error message>) on failure.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Step 1: Verify resource existence and current status
        cursor.execute(
            "SELECT id, name, status FROM resources WHERE id = ?",
            (resource_id,)
        )
        res = cursor.fetchone()
        if not res:
            return False, "Resource does not exist."

        if res["status"] != "Available":
            if res["status"] == "In Use":
                return False, f"Resource '{res['name']}' is currently in use."
            elif res["status"] == "Maintenance":
                return False, f"Resource '{res['name']}' is currently under maintenance."
            return False, f"Resource '{res['name']}' is not available (status: {res['status']})."

        # Step 2: Verify user existence
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            return False, "User does not exist."

        # Step 3: Insert booking record and update resource status atomically
        cursor.execute(
            """
            INSERT INTO bookings (resource_id, booked_by, booked_at, returned_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, NULL)
            """,
            (resource_id, user_id)
        )

        cursor.execute(
            "UPDATE resources SET status = 'In Use' WHERE id = ?",
            (resource_id,)
        )

        conn.commit()
        return True, "Resource booked successfully."

    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error while booking resource: {e}"
    finally:
        conn.close()


def return_resource(resource_id: int, user_id: int) -> tuple[bool, str]:
    """
    Return an active booking for a resource.

    Rules enforced:
      1. Resource must exist.
      2. Resource must currently be 'In Use'.
      3. An active booking (returned_at IS NULL) must exist for this resource.
      4. The active booking must have been made by user_id (cannot return
         someone else's booking).
      5. Sets returned_at = CURRENT_TIMESTAMP on the active booking.
      6. Changes resource status back to 'Available'.
      7. Executed inside a database transaction.

    Parameters:
        resource_id — ID of the resource to return
        user_id     — ID of the user returning the resource (users.id)

    Returns:
        (True, "Resource returned successfully.") on success,
        or (False, <error message>) on failure.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Step 1: Verify resource exists
        cursor.execute(
            "SELECT id, name, status FROM resources WHERE id = ?",
            (resource_id,)
        )
        res = cursor.fetchone()
        if not res:
            return False, "Resource does not exist."

        # Step 2: Resource must currently be In Use
        if res["status"] != "In Use":
            return False, f"Resource '{res['name']}' is not currently in use (status: {res['status']})."

        # Step 3: Check active booking
        cursor.execute(
            """
            SELECT id, booked_by
            FROM bookings
            WHERE resource_id = ? AND returned_at IS NULL
            """,
            (resource_id,)
        )
        active_booking = cursor.fetchone()

        if not active_booking:
            return False, "No active booking found for this resource."

        if active_booking["booked_by"] != user_id:
            return False, "You cannot return this resource because it was booked by another user."

        booking_id = active_booking["id"]

        # Step 4: Update booking returned_at and resource status atomically
        cursor.execute(
            "UPDATE bookings SET returned_at = CURRENT_TIMESTAMP WHERE id = ?",
            (booking_id,)
        )

        cursor.execute(
            "UPDATE resources SET status = 'Available' WHERE id = ?",
            (resource_id,)
        )

        conn.commit()
        return True, "Resource returned successfully."

    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error while returning resource: {e}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Maintenance operations
# ---------------------------------------------------------------------------

def set_maintenance(resource_id: int, notes: str | None = None) -> tuple[bool, str]:
    """
    Place a resource into Maintenance status.

    Rules enforced:
      1. Resource must exist.
      2. Resource cannot currently be 'In Use' (active booking present).
      3. Sets status = 'Maintenance'.
      4. Stores provided maintenance notes (or keeps existing if notes is None).
      5. Does not delete any booking history.

    Parameters:
        resource_id — ID of the resource
        notes       — String describing the reason for maintenance

    Returns:
        (True, "Resource placed under maintenance.") on success,
        or (False, <error message>) on failure.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Step 1: Verify resource
        cursor.execute(
            "SELECT id, name, status FROM resources WHERE id = ?",
            (resource_id,)
        )
        res = cursor.fetchone()
        if not res:
            return False, "Resource does not exist."

        # Step 2: Cannot place under maintenance while in use
        if res["status"] == "In Use":
            return False, f"Cannot place '{res['name']}' under maintenance because it is currently in use."

        # Clean notes
        clean_notes = notes.strip() if (notes and isinstance(notes, str)) else None

        cursor.execute(
            """
            UPDATE resources
            SET status = 'Maintenance', maintenance_notes = ?
            WHERE id = ?
            """,
            (clean_notes, resource_id)
        )
        conn.commit()
        return True, "Resource marked for maintenance."

    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error while updating maintenance: {e}"
    finally:
        conn.close()


def mark_maintenance(resource_id: int, notes: str | None = None) -> tuple[bool, str]:
    """
    Convenience function that marks a resource for maintenance.
    Delegates to set_maintenance().
    """
    return set_maintenance(resource_id, notes)


def release_maintenance(resource_id: int) -> tuple[bool, str]:
    """
    Release a resource from maintenance, making it 'Available' again.

    Rules enforced:
      1. Resource must exist.
      2. Resource must currently have status 'Maintenance'.
      3. Sets status = 'Available'.
      4. Clears maintenance_notes (sets to NULL).

    Parameters:
        resource_id — ID of the resource to release

    Returns:
        (True, "Resource released from maintenance successfully.") on success,
        or (False, <error message>) on failure.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, status FROM resources WHERE id = ?",
            (resource_id,)
        )
        res = cursor.fetchone()
        if not res:
            return False, "Resource does not exist."

        if res["status"] != "Maintenance":
            return False, f"Resource '{res['name']}' is not under maintenance (status: {res['status']})."

        cursor.execute(
            """
            UPDATE resources
            SET status = 'Available', maintenance_notes = NULL
            WHERE id = ?
            """,
            (resource_id,)
        )
        conn.commit()
        return True, "Resource released from maintenance successfully."

    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error while releasing maintenance: {e}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# History and Reporting queries
# ---------------------------------------------------------------------------

def get_user_bookings(user_id: int) -> list[dict]:
    """
    Return booking history for a specific user.

    Sorted newest first (by booking id descending).

    Columns included in each dictionary:
      - id (booking id)
      - resource_id
      - resource_code
      - resource_name
      - name (alias for resource_name)
      - booked_at
      - returned_at
      - status ('Active' if returned_at IS NULL, else 'Returned')

    Parameters:
        user_id — ID of the user (users.id)

    Returns:
        List of booking dictionaries.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                b.id,
                b.resource_id,
                b.booked_by,
                b.booked_at,
                b.returned_at,
                r.resource_code,
                r.name AS resource_name,
                r.name,
                CASE WHEN b.returned_at IS NULL THEN 'Active' ELSE 'Returned' END AS status
            FROM bookings b
            JOIN resources r ON b.resource_id = r.id
            WHERE b.booked_by = ?
            ORDER BY b.id DESC
            """,
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_booking_history() -> list[dict]:
    """
    Return complete booking history across all users for teacher/admin reporting.

    Sorted newest first (by booking id descending).

    Columns included in each dictionary:
      - id (booking id)
      - resource_id
      - resource_code
      - resource_name
      - name (alias for resource_name)
      - booked_by (user ID)
      - user_name (name of user who booked)
      - username (username of user who booked)
      - booked_at
      - returned_at
      - status ('Active' if returned_at IS NULL, else 'Returned')

    Returns:
        List of all booking dictionaries.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                b.id,
                b.resource_id,
                b.booked_by,
                b.booked_at,
                b.returned_at,
                r.resource_code,
                r.name AS resource_name,
                r.name,
                u.name AS user_name,
                u.username,
                CASE WHEN b.returned_at IS NULL THEN 'Active' ELSE 'Returned' END AS status
            FROM bookings b
            JOIN resources r ON b.resource_id = r.id
            JOIN users u ON b.booked_by = u.id
            ORDER BY b.id DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
