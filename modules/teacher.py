"""
modules/teacher.py — SCMS Teacher Menu
=======================================
Provides the teacher-facing dashboard and menus.

This is a MENU/CONTROLLER module:
  - Displays menus and collects input from the Teacher
  - Calls domain modules (resources.py, etc.)
  - Displays results to the terminal

It does NOT:
  - Run SQL queries directly
  - Handle password logic
  - Contain database transactions (delegated to domain layer)

Architecture:
  main.py → teacher_menu(user)
                → modules/resources.py → database.py → SQLite

Implemented features:
  - Resource Management (Step 12):
      * View Resources
      * Book Resource
      * Return Resource
      * My Booking History
      * Mark Resource for Maintenance
      * Release Resource from Maintenance
      * View Booking History (all users)
"""

from modules.resources import (
    get_resources,
    get_available_resources,
    get_resource_by_code,
    book_resource,
    return_resource,
    get_user_bookings,
    get_booking_history,
    set_maintenance,
    release_maintenance,
)
from modules.alerts import (
    get_active_alerts,
    create_alert,
    resolve_alert,
    get_alert_history,
)
from modules.analytics import (
    get_dashboard_summary,
    get_attendance_analytics,
    get_performance_analytics,
    get_student_performance_summary,
    get_resource_analytics,
    get_alert_analytics,
)


# ---------------------------------------------------------------------------
# Separator and display helpers
# ---------------------------------------------------------------------------

def _line(char="-", width=50):
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
# Resource Management Submenu
# ---------------------------------------------------------------------------

def manage_resources_teacher(user) -> None:
    """
    Submenu for Teacher resource management operations:
      1. View Resources
      2. Book Resource
      3. Return Resource
      4. My Booking History
      5. Mark Resource for Maintenance
      6. Release Resource from Maintenance
      7. View Booking History
      0. Back
    """
    while True:
        _header("Resource Management")
        print("  1. View Resources")
        print("  2. Book Resource")
        print("  3. Return Resource")
        print("  4. My Booking History")
        print("  5. Mark Resource for Maintenance")
        print("  6. Release Resource from Maintenance")
        print("  7. View Booking History")
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
                print(f"\n  {'Code':<10} {'Resource':<24} {'Status':<15} {'Notes'}")
                _line(width=75)
                for r in resources:
                    notes = r["maintenance_notes"] or "-"
                    print(f"  {r['resource_code']:<10} {r['name']:<24} {r['status']:<15} {notes}")
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

        # ── 5. Mark Resource for Maintenance ────────────────────────────────
        elif choice == "5":
            _header("Mark Resource for Maintenance")
            code = input("  Enter resource code (or '0' to cancel): ").strip()
            if code == "0" or not code:
                continue

            res = get_resource_by_code(code)
            if not res:
                print(f"\n  Resource '{code}' not found.")
                _pause()
                continue

            if res["status"] == "In Use":
                print(f"\n  Cannot place '{res['name']}' under maintenance because it is currently In Use.")
                _pause()
                continue

            notes = input("  Maintenance notes (optional): ").strip()
            success, msg = set_maintenance(res["id"], notes)
            print(f"\n  {msg}")
            _pause()

        # ── 6. Release Resource from Maintenance ────────────────────────────
        elif choice == "6":
            _header("Release Resource from Maintenance")
            code = input("  Enter resource code (or '0' to cancel): ").strip()
            if code == "0" or not code:
                continue

            res = get_resource_by_code(code)
            if not res:
                print(f"\n  Resource '{code}' not found.")
                _pause()
                continue

            if res["status"] != "Maintenance":
                print(f"\n  Resource '{res['name']}' is not under maintenance (currently {res['status']}).")
                _pause()
                continue

            success, msg = release_maintenance(res["id"])
            print(f"\n  {msg}")
            _pause()

        # ── 7. View Complete Booking History ────────────────────────────────
        elif choice == "7":
            _header("Complete Booking History")
            history = get_booking_history()
            if not history:
                print("\n  No booking records found in the system.")
            else:
                print(f"\n  {'Code':<8} {'Resource':<18} {'Booked By':<18} {'Booked At':<20} {'Returned At':<20} {'Status'}")
                _line(width=95)
                for b in history:
                    ret_str = b["returned_at"] if b["returned_at"] else "-"
                    print(f"  {b['resource_code']:<8} {b['resource_name']:<18} {b['user_name']:<18} {b['booked_at']:<20} {ret_str:<20} {b['status']}")
            _pause()

        else:
            print("\n  Invalid choice. Please enter a number from the menu.")
            _pause()


# ---------------------------------------------------------------------------
# Safety & Security Alerts Submenu
# ---------------------------------------------------------------------------

def manage_alerts_teacher(user) -> None:
    """
    Submenu for Teacher safety & security alert operations (software simulation):
      1. View Active Alerts
      2. Report Safety Alert
      3. Resolve Alert
      4. View Alert History
      0. Back
    """
    while True:
        _header("Safety & Security Alerts")
        print("  [Simulated Prototype — Not connected to real emergency services]")
        _line()
        print("  1. View Active Alerts")
        print("  2. Report Safety Alert")
        print("  3. Resolve Alert")
        print("  4. View Alert History")
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
                    print(f"  [ID #{a['id']}] [{a['alert_type']}]")
                    print(f"  Location    : {a['location']}")
                    print(f"  Description : {a['description']}")
                    print(f"  Created     : {a['created_at']}")
                    print(f"  Reported by : {a['creator_name']} ({a['creator_username']})")
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

        # ── 3. Resolve Alert ────────────────────────────────────────────────
        elif choice == "3":
            _header("Resolve Safety Alert")
            active_alerts = get_active_alerts()
            if not active_alerts:
                print("\n  No active safety alerts to resolve.")
                _pause()
                continue

            print("\n  Active Alerts:")
            print(f"  {'ID':<5} {'Type':<22} {'Location'}")
            _line(width=60)
            for a in active_alerts:
                print(f"  {a['id']:<5} {a['alert_type']:<22} {a['location']}")
            print()

            id_input = input("  Enter alert ID to resolve (or '0' to cancel): ").strip()
            if id_input == "0" or not id_input:
                continue

            if not id_input.isdigit():
                print("\n  Invalid alert ID. Please enter a valid number.")
                _pause()
                continue

            alert_id = int(id_input)
            success, msg = resolve_alert(alert_id, user["id"])
            print(f"\n  {msg}")
            _pause()

        # ── 4. View Alert History ────────────────────────────────────────────
        elif choice == "4":
            _header("Alert History")
            alerts = get_alert_history()
            if not alerts:
                print("\n  No alert records found.")
            else:
                print()
                for a in alerts:
                    _line()
                    print(f"  [ID #{a['id']}] [{a['alert_type']}] — Status: {a['status']}")
                    print(f"  Location    : {a['location']}")
                    print(f"  Description : {a['description']}")
                    print(f"  Created     : {a['created_at']}")
                    if a["status"] == "Resolved" and a["resolved_at"]:
                        print(f"  Resolved    : {a['resolved_at']}")
                        if a["resolver_name"]:
                            print(f"  Resolved by : {a['resolver_name']} ({a['resolver_username']})")
                    print(f"  Reported by : {a['creator_name']} ({a['creator_username']})")
                _line()
            _pause()

        else:
            print("\n  Invalid choice. Please enter a number from the menu.")
            _pause()


# ---------------------------------------------------------------------------
# Analytics & Reports Submenu
# ---------------------------------------------------------------------------

def manage_analytics_teacher(user) -> None:
    """
    Submenu for Teacher analytics and reporting:
      1. Dashboard Summary
      2. Attendance Analytics
      3. Performance Analytics
      4. Student Performance Summary
      5. Resource Usage
      6. Safety Alert Statistics
      0. Back
    """
    while True:
        _header("Analytics & Reports")
        print("  1. Dashboard Summary")
        print("  2. Attendance Analytics")
        print("  3. Performance Analytics")
        print("  4. Student Performance Summary")
        print("  5. Resource Usage")
        print("  6. Safety Alert Statistics")
        print()
        print("  0. Back")
        print()
        _line()

        choice = input("  Enter your choice: ").strip()

        # ── 0. Back ─────────────────────────────────────────────────────────
        if choice == "0":
            return

        # ── 1. Dashboard Summary ────────────────────────────────────────────
        elif choice == "1":
            _header("System Dashboard Summary")
            summary = get_dashboard_summary()
            print()
            print(f"  Students                  : {summary['total_students']}")
            print(f"  Teachers                  : {summary['total_teachers']}")
            print(f"  Resources                 : {summary['total_resources']}")
            print(f"  Active Resource Bookings  : {summary['active_resource_bookings']}")
            print(f"  Low Attendance Students   : {summary['low_attendance_students']}")
            print(f"  Low Performance Students  : {summary['low_performance_students']}")
            print(f"  Active Safety Alerts      : {summary['active_safety_alerts']}")
            print()
            _pause()

        # ── 2. Attendance Analytics ─────────────────────────────────────────
        elif choice == "2":
            _header("Attendance Analytics")
            att = get_attendance_analytics()
            if att["total_records"] == 0:
                print("\n  No attendance data available.")
            else:
                print()
                print(f"  Total Students            : {att['total_students']}")
                print(f"  Attendance Records        : {att['total_records']}")
                print(f"  Overall Attendance        : {att['overall_percentage']:.2f}%")
                print(f"  Below {int(att['threshold'])}%                 : {att['below_threshold']}")
                print(f"  {int(att['threshold'])}% or Above              : {att['above_or_equal_threshold']}")
                print()
                print("  Subject-wise Attendance")
                _line()
                for s in att["subject_attendance"]:
                    print(f"  {s['subject_name']:<30} {s['attendance_percentage']:.2f}%")
            print()
            _pause()

        # ── 3. Performance Analytics ────────────────────────────────────────
        elif choice == "3":
            _header("Performance Analytics")
            perf = get_performance_analytics()
            if perf["total_students_with_marks"] == 0:
                print("\n  No performance data available.")
            else:
                print()
                print(f"  Students With Marks       : {perf['total_students_with_marks']}")
                print(f"  Overall Performance       : {perf['overall_percentage']:.2f}%")
                print(f"  Below {int(perf['threshold'])}%                 : {perf['below_threshold']}")
                print(f"  {int(perf['threshold'])}% or Above              : {perf['above_or_equal_threshold']}")
                print()
                print("  Subject-wise Performance")
                _line()
                for s in perf["subject_performance"]:
                    print(f"  {s['subject_name']:<30} {s['performance_percentage']:.2f}%")
            print()
            _pause()

        # ── 4. Student Performance Summary ──────────────────────────────────
        elif choice == "4":
            _header("Student Performance Summary")
            students = get_student_performance_summary()
            if not students:
                print("\n  No student records found.")
            else:
                print()
                print(f"  {'Student':<20} {'Roll No':<12} {'Attendance':<18} {'Performance'}")
                _line(width=72)
                for s in students:
                    if s["attendance_percentage"] is not None:
                        att_str = f"{s['attendance_percentage']:.1f}% {s['attendance_status']}"
                    else:
                        att_str = "NO DATA"

                    if s["performance_percentage"] is not None:
                        perf_str = f"{s['performance_percentage']:.1f}% {s['performance_status']}"
                    else:
                        perf_str = "NO DATA"

                    print(f"  {s['name']:<20} {s['roll_number']:<12} {att_str:<18} {perf_str}")
            print()
            _pause()

        # ── 5. Resource Usage ───────────────────────────────────────────────
        elif choice == "5":
            _header("Resource Usage")
            res = get_resource_analytics()
            print()
            print(f"  Total Resources           : {res['total_resources']}")
            print(f"  Available                 : {res['available']}")
            print(f"  In Use                    : {res['in_use']}")
            print(f"  Maintenance               : {res['maintenance']}")
            print()
            print(f"  Total Bookings            : {res['total_bookings']}")
            print(f"  Active Bookings           : {res['active_bookings']}")
            print(f"  Completed Bookings        : {res['completed_bookings']}")
            print()
            print("  Booking Count by Resource")
            _line()
            for r in res["booking_counts"]:
                print(f"  {r['resource_code']} {r['resource_name']:<25} {r['booking_count']}")
            print()
            _pause()

        # ── 6. Safety Alert Statistics ──────────────────────────────────────
        elif choice == "6":
            _header("Safety Alert Statistics")
            alt = get_alert_analytics()
            if alt["total_alerts"] == 0:
                print("\n  No safety alert data available.")
            else:
                print()
                print(f"  Total Alerts              : {alt['total_alerts']}")
                print(f"  Active Alerts             : {alt['active_alerts']}")
                print(f"  Resolved Alerts           : {alt['resolved_alerts']}")
                print()
                print("  By Type")
                _line()
                for alert_type, count in alt["by_type"].items():
                    print(f"  {alert_type:<25} {count}")
            print()
            _pause()

        else:
            print("\n  Invalid choice. Please enter a number from the menu.")
            _pause()


# ---------------------------------------------------------------------------
# Teacher menu
# ---------------------------------------------------------------------------

def teacher_menu(user) -> None:
    """
    Display the teacher dashboard and handle menu choices.

    Loops until the teacher selects Logout (option 0).
    Returns to main.py when done — does not exit the program.

    Parameters:
        user — sqlite3.Row from authenticate_user()
                Access fields: user["name"], user["id"], user["role"]
    """
    while True:
        _header("Teacher Dashboard")
        print(f"  Welcome, {user['name']}!")
        print(f"  Role   : Teacher")
        _line()
        print()
        print("  1. Mark Attendance")
        print("  2. View Attendance Report")
        print("  3. Enter Marks")
        print("  4. View Class Performance")
        print("  5. View Learning Gaps")
        print("  6. Resource Management")
        print("  7. Safety & Security Alerts")
        print("  8. Analytics & Reports")
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

        elif choice == "6":
            manage_resources_teacher(user)

        elif choice == "7":
            manage_alerts_teacher(user)

        elif choice == "8":
            manage_analytics_teacher(user)

        elif choice in ("1", "2", "3", "4", "5"):
            print()
            print("  [This feature is not yet implemented.]")
            print("  It will be available in a later development step.")
            _pause()

        else:
            print()
            print("  Invalid choice. Please enter a number from the menu.")
            _pause()
