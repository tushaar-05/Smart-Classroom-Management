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
        print("  7. Raise Safety Alert")
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

        elif choice in ("1", "2", "3", "4", "5", "7"):
            print()
            print("  [This feature is not yet implemented.]")
            print("  It will be available in a later development step.")
            _pause()

        else:
            print()
            print("  Invalid choice. Please enter a number from the menu.")
            _pause()
