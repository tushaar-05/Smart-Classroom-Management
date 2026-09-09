"""
modules/student.py — SCMS Student Menu
=======================================
Provides the student-facing dashboard and all student-level features.

This is a MENU/CONTROLLER module. It:
  - Displays menus and collects input from the Student
  - Calls domain modules (attendance.py, future: marks.py, etc.)
  - Displays results to the terminal

It does NOT:
  - Run SQL queries directly
  - Handle password logic
  - Perform data calculations

Architecture:
    main.py → student_menu(user) → attendance.py → database.py → SQLite

Currently implemented (Step 8):
  - View Attendance (subject-wise + overall)

Planned for later steps:
  - View Marks
  - Learning Gap Report
  - Learning Assistant

The `user` parameter is the sqlite3.Row returned by authenticate_user().
Access fields as: user["id"], user["name"], user["role"], etc.

IMPORTANT: user["id"] is users.id, which is NOT the same as students.id.
attendance.py.get_student_id() resolves this mapping.
"""

from modules.attendance import (
    get_student_id,
    get_overall_attendance,
    get_subject_attendance,
)


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
        print()
        print("  --- (Coming soon) ---")
        print("  2. View Marks")
        print("  3. Learning Gap Report")
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

        elif choice in ("2", "3", "4"):
            print()
            print("  This feature is not yet implemented.")
            print("  It will be available in a later development step.")
            _pause()

        else:
            print()
            print("  Invalid choice. Please enter a number from the menu.")
            _pause()
