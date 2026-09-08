"""
main.py — SCMS Application Entry Point
=======================================
This is the first file Python runs: `python3 main.py`

Responsibilities:
  1. Initialize the database (create tables if first run).
  2. Display the SCMS welcome banner.
  3. Show a login prompt and collect credentials securely.
  4. Pass credentials to auth.py for verification.
  5. Route the authenticated user to their role menu.
  6. Loop back to the login screen after logout.
  7. Exit cleanly when the user chooses to quit.

What this file does NOT do:
  - Password hashing or verification (→ modules/auth.py)
  - Feature logic such as attendance or marks (→ domain modules)
  - Direct database queries (→ database.py / domain modules)

Architecture reminder:
    main.py
        ↓ initializes
    database.py
        ↓ calls
    modules/auth.py          (authentication)
        ↓ routes to
    modules/student.py   |   modules/teacher.py   |   modules/admin.py
        ↓ will later call
    domain modules  →  database.py  →  SQLite
"""

import getpass  # Hides password input so it is not visible while typing.
import sys

from database import init_db
from modules.auth import authenticate_user
from modules.student import student_menu
from modules.teacher import teacher_menu
from modules.admin   import admin_menu


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _line(char="=", width=44):
    """Print a horizontal separator line."""
    print(char * width)


def _clear_line():
    """Print a blank line for visual spacing."""
    print()


def show_banner():
    """
    Display the SCMS welcome banner at application startup.
    Called once when the program starts.
    """
    _clear_line()
    _line()
    print("   Smart Classroom Management System")
    print("   SCMS  |  College Prototype  |  v1.0")
    _line()
    _clear_line()


def show_login_banner():
    """
    Display a smaller header above the login prompt.
    Called every time the login screen is shown (including after logout).
    """
    _line("-")
    print("  Login")
    _line("-")
    _clear_line()


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------

def login() -> dict | None:
    """
    Prompt the user for credentials and attempt authentication.

    Uses getpass.getpass() for the password so the characters typed
    are not echoed to the terminal — the cursor just waits silently.

    Returns:
        The sqlite3.Row user record on successful login.
        None if the user chose to exit (typed '0' at the username prompt).
    """
    show_login_banner()

    print("  Type '0' at the username prompt to exit the application.")
    _clear_line()

    username = input("  Username: ").strip()

    # Allow the user to exit from the login screen.
    if username == "0":
        return None

    # getpass hides the password — nothing is printed while typing.
    password = getpass.getpass("  Password: ")

    _clear_line()

    # Delegate all authentication logic to auth.py.
    user = authenticate_user(username, password)

    if user is None:
        # Do NOT say whether the username or password was wrong — generic message.
        print("  Invalid username or password. Please try again.")
        _clear_line()

    return user


# ---------------------------------------------------------------------------
# Role routing
# ---------------------------------------------------------------------------

def route_to_menu(user) -> None:
    """
    Send the authenticated user to the correct role-specific menu.

    Each menu function runs in a loop until the user logs out,
    then returns here. After returning, the main loop shows the
    login screen again.

    Parameters:
        user — sqlite3.Row returned by authenticate_user()
    """
    role = user["role"]

    if role == "student":
        student_menu(user)

    elif role == "teacher":
        teacher_menu(user)

    elif role == "admin":
        admin_menu(user)

    else:
        # This should never happen if the database schema CHECK constraint
        # is working, but we handle it gracefully just in case.
        print(f"  Unknown role '{role}'. Contact your administrator.")
        _clear_line()


# ---------------------------------------------------------------------------
# Main application loop
# ---------------------------------------------------------------------------

def main():
    """
    Main application loop.

    Flow:
        start
          ├─ init_db()               (create tables if first run)
          ├─ show banner             (once)
          └─ loop:
               ├─ login()
               │    ├─ user typed '0' → exit
               │    ├─ credentials wrong → loop again
               │    └─ credentials correct → route_to_menu()
               │            └─ user selects Logout → back to loop
               └─ continue until exit
    """
    # Step 1: Initialize the database.
    # Creates the data/ folder and scms.db if they do not exist.
    # If they already exist, this call is a safe no-op.
    init_db()

    # Step 2: Show the welcome banner exactly once at startup.
    show_banner()

    # Step 3: Login loop — runs until the user explicitly exits.
    while True:
        user = login()

        # login() returns None only when the user typed '0' to exit.
        if user is None:
            _clear_line()
            print("  Thank you for using SCMS. Goodbye!")
            _clear_line()
            sys.exit(0)

        # Successful login — route to the appropriate role menu.
        # The menu function returns when the user logs out.
        route_to_menu(user)

        # After logout, the while loop repeats and shows the login screen again.


# ---------------------------------------------------------------------------
# Entry point guard
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # This guard ensures main() is only called when this file is run
    # directly (`python3 main.py`), not when it is imported by another
    # module or a test script.
    main()
