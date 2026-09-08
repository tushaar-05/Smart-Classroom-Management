"""
modules/student.py — SCMS Student Menu
=======================================
Provides the student-facing dashboard and menu.

This is a MENU module — it handles:
  - Printing menus to the terminal
  - Collecting numbered choices from the student
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

from modules.auth import authenticate_user  # used only for the type hint context


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
# Student menu
# ---------------------------------------------------------------------------

def student_menu(user) -> None:
    """
    Display the student dashboard and handle menu choices.

    Loops until the student selects Logout (option 1).
    Returns to main.py when done — does not exit the program.

    Parameters:
        user — sqlite3.Row from authenticate_user()
                Access fields: user["name"], user["id"], user["role"]
    """
    while True:
        _header("Student Dashboard")
        print(f"  Welcome, {user['name']}!")
        print(f"  Role   : Student")
        _line()
        print()
        print("  [Coming soon — features under development]")
        print()
        print("  1. View Profile")
        print("  2. View Attendance")
        print("  3. View Marks")
        print("  4. Learning Gap Report")
        print("  5. Learning Assistant")
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

        elif choice in ("1", "2", "3", "4", "5"):
            print()
            print("  [This feature is not yet implemented.]")
            print("  It will be available in a later development step.")
            input("  Press Enter to continue...")

        else:
            print()
            print("  Invalid choice. Please enter a number from the menu.")
            input("  Press Enter to continue...")
