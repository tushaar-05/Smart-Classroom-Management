"""
modules/attendance.py — SCMS Attendance Domain Module
======================================================
Handles all attendance-related data queries for SCMS.

This is a DOMAIN module. It:
  - Queries SQLite via database.get_connection()
  - Calculates attendance statistics
  - Returns data as plain Python dictionaries/lists
  - Contains no user-input calls, menus, or print() statements

It is called by:
  - modules/student.py  (for student attendance viewing)
  - modules/teacher.py  (future: for marking attendance)
  - modules/admin.py    (future: for attendance reports)

Attendance data relationships (read this carefully):
  users.id
    └── students.user_id
          └── students.id
                └── attendance.student_id
                      └── attendance.subject_id → subjects.id

Do NOT assume users.id == students.id.
Always look up the student record using user_id.

Schema reference: docs/SCHEMA.md
"""

from database import get_connection

# ---------------------------------------------------------------------------
# Threshold configuration
# ---------------------------------------------------------------------------

# Attendance below this percentage is flagged as LOW.
# Attendance at or above this percentage is flagged as GOOD.
# Defined once here so it only needs to change in one place.
ATTENDANCE_THRESHOLD = 75.0


# ---------------------------------------------------------------------------
# Helper: attendance status label
# ---------------------------------------------------------------------------

def _status(percentage: float) -> str:
    """
    Return "LOW" or "GOOD" based on the attendance percentage.

    Uses the ATTENDANCE_THRESHOLD constant so the cutoff is defined
    in exactly one place in the codebase.

    Parameters:
        percentage — a float between 0 and 100

    Returns:
        "LOW"  if percentage < ATTENDANCE_THRESHOLD
        "GOOD" if percentage >= ATTENDANCE_THRESHOLD
    """
    return "GOOD" if percentage >= ATTENDANCE_THRESHOLD else "LOW"


# ---------------------------------------------------------------------------
# 1. Resolve users.id → students.id
# ---------------------------------------------------------------------------

def get_student_id(user_id: int) -> int | None:
    """
    Find the students table primary key for a given users.id.

    Why this is needed:
        The attendance table uses students.id (the student profile ID),
        NOT users.id (the login account ID). Every student user has:
          - one row in users  (for login / role)
          - one row in students (for roll number, class assignment)
        These two rows have DIFFERENT IDs.

    SQL:
        SELECT id FROM students WHERE user_id = ?

    Parameters:
        user_id — the id from the users table (i.e. user["id"])

    Returns:
        students.id (integer) if a student record exists for this user.
        None if the user has no corresponding student record.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM students WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        # fetchone() returns None if no row matched.
        return row["id"] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. Subject-wise attendance
# ---------------------------------------------------------------------------

def get_subject_attendance(student_id: int) -> list[dict]:
    """
    Return attendance statistics broken down by subject.

    For each subject the student has attendance records in, returns:
        subject_name — str   : display name of the subject
        present      — int   : number of Present records
        absent       — int   : number of Absent records
        total        — int   : present + absent (all records)
        percentage   — float : present / total * 100  (0 if total == 0)
        status       — str   : "GOOD" or "LOW"

    SQL strategy:
        JOIN attendance → subjects to get the subject name.
        GROUP BY subject_id so each subject gets its own row.
        Use SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) to count
        Present records without fetching every row into Python.

    Example output:
        [
            {
                "subject_name": "Mathematics",
                "present": 14, "absent": 4, "total": 18,
                "percentage": 77.78, "status": "GOOD"
            },
            ...
        ]

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        List of dicts, one per subject. Empty list if no records.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                subjects.name                                          AS subject_name,
                SUM(CASE WHEN attendance.status = 'Present' THEN 1
                         ELSE 0 END)                                   AS present,
                SUM(CASE WHEN attendance.status = 'Absent'  THEN 1
                         ELSE 0 END)                                   AS absent,
                COUNT(*)                                               AS total
            FROM attendance
            JOIN subjects ON attendance.subject_id = subjects.id
            WHERE attendance.student_id = ?
            GROUP BY attendance.subject_id
            ORDER BY subjects.name
            """,
            (student_id,)
        ).fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        total   = row["total"]
        present = row["present"]
        absent  = row["absent"]

        # Guard against division by zero (total should never be 0 here
        # because a GROUP BY row implies at least one record, but we
        # check explicitly to be safe).
        pct = (present / total * 100) if total > 0 else 0.0

        results.append({
            "subject_name": row["subject_name"],
            "present"     : present,
            "absent"      : absent,
            "total"       : total,
            "percentage"  : pct,
            "status"      : _status(pct),
        })

    return results


# ---------------------------------------------------------------------------
# 3. Overall attendance
# ---------------------------------------------------------------------------

def get_overall_attendance(student_id: int) -> dict | None:
    """
    Return overall attendance statistics across ALL subjects combined.

    Why NOT average the subject percentages:
        If Mathematics has 18 records and Programming has 5, simply
        averaging those two percentages gives a distorted result.
        Instead, we sum all raw Present/Total counts first, then
        divide — this treats every attendance day equally.

    Example:
        Mathematics: 14/18
        Programming: 16/18
        DBMS:        15/18
        Overall:     (14+16+15) / (18+18+18) = 45/54 = 83.33%
        NOT: (77.78 + 88.89 + 83.33) / 3 = 83.33% (coincidence here)

    SQL strategy:
        No GROUP BY — collapse everything into one aggregate row.
        Use SUM(CASE...) for present count, COUNT(*) for total.

    Returns:
        Dict with keys: present, absent, total, percentage, status
        None if the student has no attendance records at all.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present,
                SUM(CASE WHEN status = 'Absent'  THEN 1 ELSE 0 END) AS absent,
                COUNT(*)                                              AS total
            FROM attendance
            WHERE student_id = ?
            """,
            (student_id,)
        ).fetchone()
    finally:
        conn.close()

    # fetchone() always returns a row (even for aggregates with no matching
    # data), but COUNT(*) will be 0 if there are no records.
    if row is None or row["total"] == 0:
        return None

    total   = row["total"]
    present = row["present"]
    absent  = row["absent"]
    pct     = present / total * 100   # total > 0 confirmed above

    return {
        "present"   : present,
        "absent"    : absent,
        "total"     : total,
        "percentage": pct,
        "status"    : _status(pct),
    }
