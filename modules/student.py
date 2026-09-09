"""
modules/student.py — SCMS Student Menu
=======================================
Provides the student-facing dashboard and all student-level features.

This is a MENU/CONTROLLER module. It:
  - Displays menus and collects input from the Student
  - Calls domain modules (attendance.py, marks.py, learning_gap.py, etc.)
  - Displays results to the terminal

It does NOT:
  - Run SQL queries directly
  - Handle password logic
  - Perform data calculations

Architecture:
    main.py → student_menu(user)
                  → attendance.py / marks.py / learning_gap.py
                        → database.py → SQLite

Currently implemented (Step 10):
  - View Attendance (subject-wise + overall)    [Step 8]
  - View Marks (test-wise + subject + overall)  [Step 9]
  - Learning Gaps (rule-based detection)        [Step 10]

Planned for later steps:
  - Learning Assistant

The `user` parameter is the sqlite3.Row returned by authenticate_user().
Access fields as: user["id"], user["name"], user["role"], etc.

IMPORTANT: user["id"] is users.id, which is NOT the same as students.id.
get_student_id() from attendance.py resolves this mapping for all features.
"""

from modules.attendance import (
    get_student_id,
    get_overall_attendance,
    get_subject_attendance,
)
from modules.marks import (
    get_test_marks,
    get_subject_performance,
    get_overall_performance,
)
from modules.learning_gap import get_learning_gaps


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _line(char="-", width=46):
    """Print a horizontal separator line."""
    print(char * width)


def _header(title: str):
    """Print a formatted section header."""
    print()
    _line("=")
    print(f"  {title}")
    _line("=")


def _pause():
    """Wait for the user to press Enter before returning."""
    input("\n  Press Enter to continue...")


# ---------------------------------------------------------------------------
# Attendance viewing
# ---------------------------------------------------------------------------

def show_attendance(user) -> None:
    """
    Display the student's attendance: overall summary + subject-wise breakdown.

    Steps:
      1. Resolve users.id → students.id via attendance.get_student_id()
      2. Fetch overall attendance via attendance.get_overall_attendance()
      3. Fetch per-subject attendance via attendance.get_subject_attendance()
      4. Display both to the terminal.

    Handles the no-student-record case and the no-attendance-record case
    gracefully (no division by zero, clear messages).

    Parameters:
        user — sqlite3.Row with at least user["id"] and user["name"]
    """
    # ── Step 1: Resolve users.id → students.id ───────────────────────────────
    #
    # user["id"] is the primary key from the USERS table (login account).
    # attendance records reference STUDENTS.id (student profile).
    # These are different columns — we must look up the mapping.
    #
    student_id = get_student_id(user["id"])

    if student_id is None:
        _header("Attendance")
        print()
        print("  No student profile found for your account.")
        print("  Please contact your administrator.")
        _pause()
        return

    # ── Step 2: Fetch data from attendance.py ────────────────────────────────
    overall  = get_overall_attendance(student_id)    # dict or None
    subjects = get_subject_attendance(student_id)    # list of dicts

    # ── Step 3: Display ───────────────────────────────────────────────────────
    _header("Attendance")

    # ── Overall attendance block ──────────────────────────────────────────────
    print()
    print("  Overall Attendance")
    _line()

    if overall is None:
        print("  No attendance records found.")
        _pause()
        return

    pct_str = f"{overall['percentage']:.2f}%"
    print(f"  Present  : {overall['present']}")
    print(f"  Absent   : {overall['absent']}")
    print(f"  Total    : {overall['total']}")
    print(f"  Percent  : {pct_str}")
    print(f"  Status   : {overall['status']}")

    if overall["status"] == "LOW":
        print()
        print("  ⚠  WARNING: Your attendance is below 75%.")
        print("     Please consult your teacher or administrator.")

    # ── Subject-wise attendance block ─────────────────────────────────────────
    print()
    print()
    print("  Subject-wise Attendance")
    _line()

    if not subjects:
        print("  No subject attendance records found.")
        _pause()
        return

    # Column headers
    col_subject = 24
    col_present = 9
    col_absent  = 9
    col_total   = 8
    col_pct     = 10
    col_status  = 6

    header = (
        f"  {'Subject':<{col_subject}}"
        f"{'Present':<{col_present}}"
        f"{'Absent':<{col_absent}}"
        f"{'Total':<{col_total}}"
        f"{'Percent':<{col_pct}}"
        f"Status"
    )
    print(header)
    _line()

    for s in subjects:
        pct_label = f"{s['percentage']:.2f}%"
        row = (
            f"  {s['subject_name']:<{col_subject}}"
            f"{s['present']:<{col_present}}"
            f"{s['absent']:<{col_absent}}"
            f"{s['total']:<{col_total}}"
            f"{pct_label:<{col_pct}}"
            f"{s['status']}"
        )
        print(row)

    print()
    _pause()


# ---------------------------------------------------------------------------
# Marks & Performance viewing
# ---------------------------------------------------------------------------

def show_marks(user) -> None:
    """
    Display the student's marks and academic performance.

    Three sections are shown:
      1. Overall performance  (raw SUM totals across all tests)
      2. Subject performance  (weighted SUM per subject)
      3. Individual tests     (one row per test, sorted by subject + date)

    Student ID mapping:
      user["id"] (users.id) → get_student_id() → students.id
      marks.student_id references students.id, NOT users.id.
      We reuse get_student_id() imported from attendance.py — this is
      a shared utility that both features need, so it lives in one place.

    Parameters:
        user — sqlite3.Row with at least user["id"] and user["name"]
    """
    # ── Resolve users.id → students.id ────────────────────────────────────────
    student_id = get_student_id(user["id"])

    if student_id is None:
        _header("Marks & Performance")
        print()
        print("  No student profile found for your account.")
        print("  Please contact your administrator.")
        _pause()
        return

    # ── Fetch data from marks.py ───────────────────────────────────────────────
    overall  = get_overall_performance(student_id)    # dict or None
    subjects = get_subject_performance(student_id)    # list of dicts
    tests    = get_test_marks(student_id)             # list of dicts

    # ── Header ────────────────────────────────────────────────────────────────
    _header("Marks & Performance")

    # ── Section 1: Overall performance ────────────────────────────────────────
    print()
    print("  Overall Performance")
    _line()

    if overall is None:
        print("  No marks records found.")
        _pause()
        return

    print(f"  Obtained  : {overall['obtained']}")
    print(f"  Maximum   : {overall['maximum']}")
    print(f"  Percent   : {overall['percentage']:.2f}%")
    print(f"  Status    : {overall['status']}")

    if overall["status"] == "NEEDS IMPROVEMENT":
        print()
        print("  ⚠  Your overall performance is below 50%.")
        print("     Consider reviewing your study plan.")

    # ── Section 2: Subject-wise performance ───────────────────────────────────
    print()
    print()
    print("  Subject Performance")
    _line()

    if not subjects:
        print("  No subject marks found.")
    else:
        # Column widths
        cw_subj = 26
        cw_obt  = 11
        cw_max  = 10
        cw_pct  = 10

        hdr = (
            f"  {'Subject':<{cw_subj}}"
            f"{'Obtained':<{cw_obt}}"
            f"{'Maximum':<{cw_max}}"
            f"{'Percent':<{cw_pct}}"
            f"Status"
        )
        print(hdr)
        _line()

        for s in subjects:
            pct_label = f"{s['percentage']:.2f}%"
            print(
                f"  {s['subject_name']:<{cw_subj}}"
                f"{s['obtained']:<{cw_obt}}"
                f"{s['maximum']:<{cw_max}}"
                f"{pct_label:<{cw_pct}}"
                f"{s['status']}"
            )

    # ── Section 3: Test-wise marks ─────────────────────────────────────────────
    print()
    print()
    print("  Test-wise Marks")
    _line()

    if not tests:
        print("  No test records found.")
    else:
        cw_subj  = 26
        cw_test  = 16
        cw_score = 12
        cw_pct   = 10

        hdr = (
            f"  {'Subject':<{cw_subj}}"
            f"{'Test':<{cw_test}}"
            f"{'Score':<{cw_score}}"
            f"{'Percent':<{cw_pct}}"
            f"Date"
        )
        print(hdr)
        _line()

        for t in tests:
            score_label = f"{t['marks_obtained']}/{t['max_marks']}"
            pct_label   = f"{t['percentage']:.2f}%"
            print(
                f"  {t['subject_name']:<{cw_subj}}"
                f"{t['test_name']:<{cw_test}}"
                f"{score_label:<{cw_score}}"
                f"{pct_label:<{cw_pct}}"
                f"{t['date']}"
            )

    print()
    _pause()


# ---------------------------------------------------------------------------
# Learning Gap view
# ---------------------------------------------------------------------------

def show_learning_gaps(user) -> None:
    """
    Display the student's learning gap analysis.

    Combines subject attendance and subject performance into a single
    per-subject gap report with priority (HIGH / MEDIUM / NONE) and
    a deterministic recommendation.

    This is a RULE-BASED system — no AI, no ML, no external APIs.

    Parameters:
        user — sqlite3.Row with at least user["id"] and user["name"]
    """
    # ── Resolve users.id → students.id ─────────────────────────────────────────
    student_id = get_student_id(user["id"])

    if student_id is None:
        _header("Learning Gap Analysis")
        print()
        print("  No student profile found for your account.")
        print("  Please contact your administrator.")
        _pause()
        return

    # ── Fetch gap data from learning_gap.py ─────────────────────────────────
    gaps = get_learning_gaps(student_id)    # list of dicts

    _header("Learning Gap Analysis")

    if not gaps:
        print()
        print("  No attendance or performance data available yet.")
        _pause()
        return

    # ── Subject summary table ──────────────────────────────────────────────────
    print()
    cw_subj  = 24
    cw_att   = 15
    cw_perf  = 15
    cw_gap   = 7

    hdr = (
        f"  {'Subject':<{cw_subj}}"
        f"{'Attendance':<{cw_att}}"
        f"{'Performance':<{cw_perf}}"
        f"{'Gap':<{cw_gap}}"
        f"Priority"
    )
    print(hdr)
    _line()

    for g in gaps:
        # Format attendance cell
        if g["attendance_percentage"] is not None:
            att_cell = f"{g['attendance_percentage']:.1f}% {g['attendance_status']}"
        else:
            att_cell = g["attendance_status"]    # "NO DATA"

        # Format performance cell
        if g["performance_percentage"] is not None:
            # Abbreviate NEEDS IMPROVEMENT to NI for column width
            pstat = "NI" if g["performance_status"] == "NEEDS IMPROVEMENT" else g["performance_status"]
            perf_cell = f"{g['performance_percentage']:.1f}% {pstat}"
        else:
            perf_cell = g["performance_status"]  # "NO DATA"

        gap_cell = "YES" if g["learning_gap"] else "NO "

        print(
            f"  {g['subject_name']:<{cw_subj}}"
            f"{att_cell:<{cw_att}}"
            f"{perf_cell:<{cw_perf}}"
            f"{gap_cell:<{cw_gap}}"
            f"{g['priority']}"
        )

    # ── Check whether any gap exists ─────────────────────────────────────────────
    gap_subjects = [g for g in gaps if g["learning_gap"]]

    print()
    print()
    if not gap_subjects:
        print("  No immediate learning gaps detected.")
        print("  Keep up the good work!")
    else:
        # ── Recommendations block ──────────────────────────────────────────────
        print("  Recommendations")
        _line()
        for g in gap_subjects:
            print(f"  {g['subject_name']}:")
            print(f"    {g['recommendation']}")
            print()

    print()
    _pause()


# ---------------------------------------------------------------------------
# Student dashboard
# ---------------------------------------------------------------------------

def student_menu(user) -> None:
    """
    Display the Student dashboard and route to student features.

    Loops until the student selects Logout (option 0).
    Returns to main.py login loop when done — does not call sys.exit().

    Parameters:
        user — sqlite3.Row from authenticate_user()
                Fields: user["id"], user["name"], user["role"]
    """
    while True:
        _header("Student Dashboard")
        print(f"  Welcome, {user['name']}!")
        print(f"  Role   : Student")
        _line()
        print()
        print("  1. View Attendance")
        print("  2. View Marks")
        print("  3. Learning Gaps")
        print()
        print("  --- (Coming soon) ---")
        print("  4. Learning Assistant")
        print()
        print("  0. Logout")
        print()
        _line()

        choice = input("  Enter your choice: ").strip()

        if choice == "0":
            print()
            print(f"  Goodbye, {user['name']}! Logging out...")
            print()
            return  # Return to login loop in main.py

        elif choice == "1":
            show_attendance(user)

        elif choice == "2":
            show_marks(user)

        elif choice == "3":
            show_learning_gaps(user)

        elif choice == "4":
            print()
            print("  This feature is not yet implemented.")
            print("  It will be available in a later development step.")
            _pause()

        else:
            print()
            print("  Invalid choice. Please enter a number from the menu.")
            _pause()
