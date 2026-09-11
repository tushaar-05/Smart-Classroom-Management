"""
modules/student.py — SCMS Student Menu
=======================================
Provides the student-facing dashboard and all student-level features.

This is a MENU/CONTROLLER module. It:
  - Displays menus and collects input from the Student
  - Calls domain modules (attendance.py, marks.py, learning_gap.py,
    learning_assistant.py, etc.)
  - Displays results to the terminal

It does NOT:
  - Run SQL queries directly
  - Handle password logic
  - Perform data calculations

Architecture:
    main.py → student_menu(user)
                  → attendance.py / marks.py
                  → learning_gap.py
                  → learning_assistant.py
                        → database.py → SQLite

Currently implemented (Step 11):
  - View Attendance (subject-wise + overall)         [Step 8]
  - View Marks (test-wise + subject + overall)       [Step 9]
  - Learning Gaps (rule-based detection)             [Step 10]
  - Learning Assistant (rule-based fixed queries)    [Step 11]

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
from modules.learning_assistant import (
    get_attendance_summary,
    get_performance_summary,
    get_gaps_summary,
    get_improvement_advice,
    get_subject_info,
    get_enrolled_subjects,
)
from modules.resources import (
    get_resources,
    get_available_resources,
    get_resource_by_code,
    book_resource,
    return_resource,
    get_user_bookings,
)
from modules.alerts import (
    get_active_alerts,
    create_alert,
    get_alert_history,
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
# Learning Assistant
# ---------------------------------------------------------------------------

def show_learning_assistant(user) -> None:
    """
    Run the rule-based Learning Assistant for the student.

    This is a FIXED-QUERY assistant, not an AI chatbot.
    It answers predefined questions using actual database data.

    Options:
        1 — My attendance summary
        2 — My performance / marks summary
        3 — My learning gaps
        4 — What should I improve?
        5 — Ask about a specific subject
        0 — Back to Student Dashboard

    All data is fetched via learning_assistant.py domain functions.
    This function only handles terminal I/O (input/output).
    """
    # Resolve users.id → students.id once for the whole session.
    student_id = get_student_id(user["id"])

    if student_id is None:
        _header("Learning Assistant")
        print()
        print("  No student profile found for your account.")
        print("  Please contact your administrator.")
        _pause()
        return

    while True:
        _header("Learning Assistant")
        print(f"  Hello, {user['name']}! I can answer questions")
        print(f"  about your attendance, marks, and learning gaps.")
        _line()
        print()
        print("  1. My attendance")
        print("  2. My marks")
        print("  3. My learning gaps")
        print("  4. What should I improve?")
        print("  5. Ask about a subject")
        print()
        print("  0. Back")
        print()
        _line()

        choice = input("  Enter your choice: ").strip()

        # ── Option 1: Attendance summary ─────────────────────────────────────
        if choice == "0":
            return

        elif choice == "1":
            _header("Your Attendance")
            summaries = get_attendance_summary(student_id)
            if not summaries:
                print()
                print("  No attendance data found.")
            else:
                print()
                for s in summaries:
                    if s["attendance_percentage"] is not None:
                        pct_str = f"{s['attendance_percentage']:.2f}%"
                    else:
                        pct_str = "NO DATA"
                    print(f"  {s['subject_name']}: {pct_str} - {s['attendance_status']}")
            _pause()

        # ── Option 2: Marks / performance summary ────────────────────────────
        elif choice == "2":
            _header("Your Marks & Performance")
            summaries = get_performance_summary(student_id)
            if not summaries:
                print()
                print("  No marks data found.")
            else:
                print()
                for s in summaries:
                    if s["performance_percentage"] is not None:
                        pct_str = f"{s['performance_percentage']:.2f}%"
                    else:
                        pct_str = "NO DATA"
                    print(f"  {s['subject_name']}: {pct_str} - {s['performance_status']}")
            _pause()

        # ── Option 3: Learning gaps ───────────────────────────────────────────
        elif choice == "3":
            _header("Your Learning Gaps")
            gaps = get_gaps_summary(student_id)
            if not gaps:
                print()
                print("  No attendance or performance data found.")
            else:
                gap_subjects = [g for g in gaps if g["learning_gap"]]
                if not gap_subjects:
                    print()
                    print("  No immediate learning gaps were detected.")
                    print("  Keep up the good work!")
                else:
                    print()
                    for g in gap_subjects:
                        print(f"  {g['subject_name']} [{g['priority']}]")
                        print(f"    {g['recommendation']}")
                        print()
            _pause()

        # ── Option 4: What should I improve? ─────────────────────────────────
        elif choice == "4":
            _header("What Should I Improve?")
            advice = get_improvement_advice(student_id)
            print()
            # Print the top-level message (may be multi-line)
            for line in advice["message"].splitlines():
                print(f"  {line}")

            if advice["has_high"] or advice["has_medium"]:
                print()
                print("  Recommendations:")
                _line()
                shown = advice["high_gaps"] + advice["medium_gaps"]
                for g in shown:
                    print(f"  {g['subject_name']} [{g['priority']}]:")
                    print(f"    {g['recommendation']}")
                    print()
            _pause()

        # ── Option 5: Ask about a specific subject ────────────────────────────
        elif choice == "5":
            enrolled = get_enrolled_subjects(student_id)
            if not enrolled:
                print()
                print("  No subject data found for your profile.")
                _pause()
                continue

            _header("Ask About a Subject")
            print()
            print("  Your enrolled subjects:")
            for name in enrolled:
                print(f"    - {name}")
            print()
            query = input("  Enter subject name: ").strip()

            if not query:
                continue

            result = get_subject_info(student_id, query)

            if result is None:
                print()
                print("  Subject not found.")
                print("  Please enter one of your enrolled subjects.")
            else:
                print()
                print(f"  {result['subject_name']}")
                _line()
                # Attendance
                if result["attendance_percentage"] is not None:
                    att_str = f"{result['attendance_percentage']:.2f}%"
                else:
                    att_str = "NO DATA"
                print(f"  Attendance   : {att_str} - {result['attendance_status']}")

                # Performance
                if result["performance_percentage"] is not None:
                    perf_str = f"{result['performance_percentage']:.2f}%"
                else:
                    perf_str = "NO DATA"
                print(f"  Performance  : {perf_str} - {result['performance_status']}")

                print(f"  Priority     : {result['priority']}")
                print()
                print(f"  Recommendation:")
                print(f"    {result['recommendation']}")

            _pause()

        else:
            print()
            print("  I can currently help with attendance, marks, learning gaps,")
            print("  and subject improvement. Please enter a number from 0 to 5.")
            _pause()


# ---------------------------------------------------------------------------
# Resource Management
# ---------------------------------------------------------------------------

def show_resources_student(user) -> None:
    """
    Submenu for Student resource operations:
      1. View Resources
      2. Book Resource
      3. Return Resource
      4. My Booking History
      0. Back
    """
    while True:
        _header("Resource Management")
        print("  1. View Resources")
        print("  2. Book Resource")
        print("  3. Return Resource")
        print("  4. My Booking History")
        print()
        print("  0. Back")
        print()
        _line()

        choice = input("  Enter your choice: ").strip()

        # ── 0. Back ─────────────────────────────────────────────────────────
        if choice == "0":
            return

        # ── 1. View Resources ───────────────────────────────────────────────
        elif choice == "1":
            _header("Classroom Resources")
            resources = get_resources()
            if not resources:
                print("\n  No resources found.")
            else:
                print(f"\n  {'Code':<10} {'Resource':<24} {'Status'}")
                _line()
                for r in resources:
                    print(f"  {r['resource_code']:<10} {r['name']:<24} {r['status']}")
            _pause()

        # ── 2. Book Resource ────────────────────────────────────────────────
        elif choice == "2":
            _header("Book a Resource")
            avail = get_available_resources()
            if not avail:
                print("\n  No resources are currently available for booking.")
                _pause()
                continue

            print("\n  Available Resources:")
            print(f"  {'Code':<10} {'Resource'}")
            _line()
            for r in avail:
                print(f"  {r['resource_code']:<10} {r['name']}")
            print()

            code = input("  Enter resource code (or '0' to cancel): ").strip()
            if code == "0" or not code:
                continue

            res = get_resource_by_code(code)
            if not res:
                print(f"\n  Resource '{code}' not found.")
                _pause()
                continue

            success, msg = book_resource(res["id"], user["id"])
            print(f"\n  {msg}")
            _pause()

        # ── 3. Return Resource ───────────────────────────────────────────────
        elif choice == "3":
            _header("Return a Resource")
            code = input("  Enter resource code (or '0' to cancel): ").strip()
            if code == "0" or not code:
                continue

            res = get_resource_by_code(code)
            if not res:
                print(f"\n  Resource '{code}' not found.")
                _pause()
                continue

            success, msg = return_resource(res["id"], user["id"])
            print(f"\n  {msg}")
            _pause()

        # ── 4. My Booking History ────────────────────────────────────────────
        elif choice == "4":
            _header("My Booking History")
            bookings = get_user_bookings(user["id"])
            if not bookings:
                print("\n  You have no booking history.")
            else:
                print(f"\n  {'Code':<8} {'Resource':<20} {'Booked At':<21} {'Returned At':<21} {'Status'}")
                _line(width=80)
                for b in bookings:
                    ret_str = b["returned_at"] if b["returned_at"] else "-"
                    print(f"  {b['resource_code']:<8} {b['resource_name']:<20} {b['booked_at']:<21} {ret_str:<21} {b['status']}")
            _pause()

        else:
            print("\n  Invalid choice. Please enter a number from the menu.")
            _pause()


# ---------------------------------------------------------------------------
# Safety & Security Alerts
# ---------------------------------------------------------------------------

def show_alerts_student(user) -> None:
    """
    Submenu for Student safety & security alerts (software simulation):
      1. View Active Alerts
      2. Report Safety Alert
      3. View Alert History
      0. Back
    """
    while True:
        _header("Safety & Security Alerts")
        print("  [Simulated Prototype — Not connected to real emergency services]")
        _line()
        print("  1. View Active Alerts")
        print("  2. Report Safety Alert")
        print("  3. View Alert History")
        print()
        print("  0. Back")
        print()
        _line()

        choice = input("  Enter your choice: ").strip()

        # ── 0. Back ─────────────────────────────────────────────────────────
        if choice == "0":
            return

        # ── 1. View Active Alerts ───────────────────────────────────────────
        elif choice == "1":
            _header("Active Safety Alerts")
            active_alerts = get_active_alerts()
            if not active_alerts:
                print("\n  No active safety alerts.")
            else:
                print()
                for a in active_alerts:
                    _line()
                    print(f"  [{a['alert_type']}]")
                    print(f"  Location    : {a['location']}")
                    print(f"  Description : {a['description']}")
                    print(f"  Created     : {a['created_at']}")
                    print(f"  Reported by : {a['creator_name']}")
                _line()
            _pause()

        # ── 2. Report Safety Alert ──────────────────────────────────────────
        elif choice == "2":
            _header("Report Safety Alert")
            print("  Select alert type:")
            print("  1. Fire")
            print("  2. Unauthorized Access")
            print("  3. Medical")
            print("  4. Other")
            print("  0. Cancel")
            print()

            type_choice = input("  Enter choice (0-4): ").strip()
            type_map = {
                "1": "Fire",
                "2": "Unauthorized Access",
                "3": "Medical",
                "4": "Other",
            }
            if type_choice == "0" or type_choice not in type_map:
                if type_choice != "0":
                    print("\n  Invalid alert type selected.")
                    _pause()
                continue

            alert_type = type_map[type_choice]
            location = input("  Location    : ").strip()
            if not location:
                print("\n  Location cannot be empty.")
                _pause()
                continue

            description = input("  Description : ").strip()
            if not description:
                print("\n  Description cannot be empty.")
                _pause()
                continue

            success, msg = create_alert(alert_type, location, description, user["id"])
            if success:
                print("\n  Safety alert reported successfully.")
                print("  [Note: This is a software simulation and demonstration prototype.]")
            else:
                print(f"\n  Could not report alert: {msg}")
            _pause()

        # ── 3. View Alert History ────────────────────────────────────────────
        elif choice == "3":
            _header("Alert History")
            alerts = get_alert_history()
            if not alerts:
                print("\n  No alert records found.")
            else:
                print()
                for a in alerts:
                    _line()
                    print(f"  [{a['alert_type']}] — Status: {a['status']}")
                    print(f"  Location    : {a['location']}")
                    print(f"  Description : {a['description']}")
                    print(f"  Created     : {a['created_at']}")
                    if a["status"] == "Resolved" and a["resolved_at"]:
                        print(f"  Resolved    : {a['resolved_at']}")
                        if a["resolver_name"]:
                            print(f"  Resolved by : {a['resolver_name']}")
                    print(f"  Reported by : {a['creator_name']}")
                _line()
            _pause()

        else:
            print("\n  Invalid choice. Please enter a number from the menu.")
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
        print("  4. Learning Assistant")
        print("  5. Resource Management")
        print("  6. Safety & Security Alerts")
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
            show_learning_assistant(user)

        elif choice == "5":
            show_resources_student(user)

        elif choice == "6":
            show_alerts_student(user)

        else:
            print()
            print("  Invalid choice. Please enter a number from the menu.")
            _pause()
