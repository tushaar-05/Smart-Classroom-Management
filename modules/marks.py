"""
modules/marks.py — SCMS Marks & Performance Domain Module
==========================================================
Handles all marks and academic performance queries for SCMS.

This is a DOMAIN module. It:
  - Queries SQLite via database.get_connection()
  - Calculates performance statistics
  - Returns data as plain Python dicts / lists of dicts
  - Contains no user-input calls, menus, or print() statements

It is called by:
  - modules/student.py  (student marks viewing)
  - modules/teacher.py  (future: mark entry)
  - modules/admin.py    (future: marks reports)

Performance calculation rule (used throughout this module):
  percentage = SUM(marks_obtained) / SUM(max_marks) × 100

  This is a WEIGHTED average — each test contributes proportionally
  to its maximum marks. Never average raw percentages.

Example:
  Test 1:  38 / 50
  Test 2:  42 / 50
  Mid-Term: 72 / 100

  Correct: (38+42+72) / (50+50+100) = 152/200 = 76.00%
  Wrong:   (76%+84%+72%) / 3        = 77.33%   ← distorted

Marks data relationships:
  users.id
    └── students.user_id → students.id
          └── marks.student_id
                └── marks.subject_id → subjects.id

Do NOT assume users.id == students.id.
Use get_student_id() from attendance.py (or a local equivalent).

Schema reference: docs/SCHEMA.md
"""

from database import get_connection

# ---------------------------------------------------------------------------
# Performance threshold
# ---------------------------------------------------------------------------

# A subject or overall performance below this percentage is flagged as
# NEEDS IMPROVEMENT. At or above it → GOOD.
# Defined once so a single change propagates everywhere.
PERFORMANCE_THRESHOLD = 50.0


# ---------------------------------------------------------------------------
# Status helper
# ---------------------------------------------------------------------------

def _status(percentage: float) -> str:
    """
    Return the performance status label for a given percentage.

    Returns:
        "GOOD"             if percentage >= PERFORMANCE_THRESHOLD
        "NEEDS IMPROVEMENT" if percentage < PERFORMANCE_THRESHOLD
    """
    return "GOOD" if percentage >= PERFORMANCE_THRESHOLD else "NEEDS IMPROVEMENT"


# ---------------------------------------------------------------------------
# 1. Individual test marks
# ---------------------------------------------------------------------------

def get_test_marks(student_id: int) -> list[dict]:
    """
    Return all individual test records for a student, with subject names.

    For each test, the per-test percentage is:
        marks_obtained / max_marks × 100

    The schema guarantees max_marks > 0, so no division-by-zero guard
    is needed at the per-test level.

    Results are ordered by subject name, then by date — so all tests
    for the same subject appear together in chronological order.

    SQL:
        SELECT subjects.name, marks.test_name,
               marks.marks_obtained, marks.max_marks, marks.date
        FROM marks
        JOIN subjects ON marks.subject_id = subjects.id
        WHERE marks.student_id = ?
        ORDER BY subjects.name, marks.date

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        List of dicts, one per test. Empty list if none.
        Each dict:
            subject_name    str
            test_name       str
            marks_obtained  int
            max_marks       int
            percentage      float   marks_obtained / max_marks × 100
            date            str     ISO date (YYYY-MM-DD)
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT subjects.name     AS subject_name,
                   marks.test_name,
                   marks.marks_obtained,
                   marks.max_marks,
                   marks.date
            FROM marks
            JOIN subjects ON marks.subject_id = subjects.id
            WHERE marks.student_id = ?
            ORDER BY subjects.name, marks.date
            """,
            (student_id,)
        ).fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        pct = (row["marks_obtained"] / row["max_marks"]) * 100   # max_marks > 0 guaranteed
        result.append({
            "subject_name"  : row["subject_name"],
            "test_name"     : row["test_name"],
            "marks_obtained": row["marks_obtained"],
            "max_marks"     : row["max_marks"],
            "percentage"    : pct,
            "date"          : row["date"],
        })
    return result


# ---------------------------------------------------------------------------
# 2. Subject-wise performance
# ---------------------------------------------------------------------------

def get_subject_performance(student_id: int) -> list[dict]:
    """
    Return academic performance grouped by subject.

    For each subject, the performance percentage is:
        SUM(marks_obtained) / SUM(max_marks) × 100

    This is a WEIGHTED calculation — tests worth more marks contribute
    more to the subject average.

    Why GROUP BY subject_id:
        Each subject has multiple test rows.
        GROUP BY collapses them into one summary row per subject,
        so SUM() operates on only that subject's tests.

    SQL:
        SELECT subjects.name,
               SUM(marks.marks_obtained) AS obtained,
               SUM(marks.max_marks)      AS maximum
        FROM marks
        JOIN subjects ON marks.subject_id = subjects.id
        WHERE marks.student_id = ?
        GROUP BY marks.subject_id
        ORDER BY subjects.name

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        List of dicts, one per subject. Empty list if no marks.
        Each dict:
            subject_name  str
            obtained      int    SUM(marks_obtained)
            maximum       int    SUM(max_marks)
            percentage    float  obtained / maximum × 100
            status        str    "GOOD" or "NEEDS IMPROVEMENT"
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT subjects.name              AS subject_name,
                   SUM(marks.marks_obtained)  AS obtained,
                   SUM(marks.max_marks)       AS maximum
            FROM marks
            JOIN subjects ON marks.subject_id = subjects.id
            WHERE marks.student_id = ?
            GROUP BY marks.subject_id
            ORDER BY subjects.name
            """,
            (student_id,)
        ).fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        obtained = row["obtained"]
        maximum  = row["maximum"]
        # maximum will be > 0 if any marks rows exist (schema: max_marks > 0)
        pct = (obtained / maximum) * 100 if maximum > 0 else 0.0
        result.append({
            "subject_name": row["subject_name"],
            "obtained"    : obtained,
            "maximum"     : maximum,
            "percentage"  : pct,
            "status"      : _status(pct),
        })
    return result


# ---------------------------------------------------------------------------
# 3. Overall performance
# ---------------------------------------------------------------------------

def get_overall_performance(student_id: int) -> dict | None:
    """
    Return overall academic performance across ALL tests in ALL subjects.

    The overall percentage is:
        SUM(all marks_obtained) / SUM(all max_marks) × 100

    This is NOT:
        - an average of individual test percentages
        - an average of subject-level percentages
    Both of those would be distorted whenever tests have different max_marks.

    Example:
        Subject A tests: 38/50, 42/50, 72/100  → raw totals: 152/200
        Subject B tests: 44/50, 46/50, 80/100  → raw totals: 170/200
        Overall: (152+170) / (200+200) = 322/400 = 80.50%

    SQL:
        SELECT SUM(marks_obtained) AS obtained,
               SUM(max_marks)      AS maximum
        FROM marks
        WHERE student_id = ?

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        Dict on success:
            obtained    int
            maximum     int
            percentage  float
            status      str
        None if the student has no marks records.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT SUM(marks_obtained) AS obtained,
                   SUM(max_marks)      AS maximum
            FROM marks
            WHERE student_id = ?
            """,
            (student_id,)
        ).fetchone()
    finally:
        conn.close()

    # fetchone() always returns a row for an aggregate, but SUM() returns
    # NULL (→ None in Python) when there are no matching rows.
    if row is None or row["maximum"] is None or row["maximum"] == 0:
        return None

    obtained = row["obtained"]
    maximum  = row["maximum"]
    pct      = (obtained / maximum) * 100

    return {
        "obtained"  : obtained,
        "maximum"   : maximum,
        "percentage": pct,
        "status"    : _status(pct),
    }
