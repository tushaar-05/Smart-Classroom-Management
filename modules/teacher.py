"""
modules/teacher.py — SCMS Teacher Menu
=======================================
Provides the teacher-facing dashboard and menu.

This is a MENU module — it handles:
  - Printing menus to the terminal
  - Collecting numbered choices from the teacher
  - Calling the appropriate domain module functions

It does NOT contain:
  - Authentication logic
  - Password handling
  - Database connection setup
  - Business calculations

The `user` parameter is the sqlite3.Row object returned by
authenticate_user(). Access fields as: user["name"], user["id"], etc.

Current status: placeholder — real feature options will be added in
later implementation steps.
"""


# ---------------------------------------------------------------------------
# Separator and display helpers
# ---------------------------------------------------------------------------

def _line(char="-", width=44):
    """Print a horizontal separator line."""
    print(char * width)


def _header(title: str):
    """Print a formatted section header."""
    print()
    _line("=")
    print(f"  {title}")
    _line("=")


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
        print("  [Coming soon — features under development]")
        print()
        print("  1. Mark Attendance")
        print("  2. View Attendance Report")
        print("  3. Enter Marks")
        print("  4. View Class Performance")
        print("  5. View Learning Gaps")
        print("  6. Book a Resource")
        print("  7. Return a Resource")
        print("  8. Raise Safety Alert")
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

        elif choice in ("1", "2", "3", "4", "5", "6", "7", "8"):
            print()
            print("  [This feature is not yet implemented.]")
            print("  It will be available in a later development step.")
            input("  Press Enter to continue...")

        else:
            print()
            print("  Invalid choice. Please enter a number from the menu.")
            input("  Press Enter to continue...")
