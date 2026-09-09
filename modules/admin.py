"""
modules/admin.py — SCMS Admin Menu
=====================================
Provides the administrator-facing dashboard and all admin-level features.

This is a MENU/CONTROLLER module. It:
  - Displays menus and collects input from the Admin
  - Calls domain functions (auth.create_user) and database queries
  - Displays results

It does NOT:
  - Handle password hashing (delegated to modules/auth.py)
  - Manage database connection setup (delegated to database.py)
  - Contain business logic for attendance, marks, resources, etc.

Currently implemented features (Step 7):
  - Manage Users   → View Users, Add User
  - Manage Classes → View Classes, Add Class
  - Manage Subjects→ View Subjects, Add Subject

Planned (later steps):
  - Attendance reports
  - Marks reports
  - Learning gap view
  - Resource management
  - Safety alert resolution
  - Analytics dashboard
"""

import sqlite3

from database import get_connection
from modules.auth import create_user
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


def _subheader(title: str):
    """Print a smaller section header for submenus."""
    print()
    _line()
    print(f"  {title}")
    _line()


def _pause():
    """Pause and wait for the user to press Enter before continuing."""
    input("\n  Press Enter to continue...")


# ---------------------------------------------------------------------------
# ── USER MANAGEMENT ─────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def view_users() -> None:
    """
    Fetch all users from the database and display them in a readable table.

    Columns shown: ID, Name, Username, Role
    Columns hidden: password_hash, password_salt  (never displayed)

    SQL used:
        SELECT id, name, username, role FROM users ORDER BY role, name
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Order by role first so admins, students, teachers are grouped.
        cursor.execute(
            "SELECT id, name, username, role FROM users ORDER BY role, name"
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    _subheader("All Users")

    if not rows:
        print("  No users found.")
        _pause()
        return

    # Print a fixed-width table header.
    print(f"  {'ID':<5} {'Name':<22} {'Username':<15} {'Role':<10}")
    _line()
    for row in rows:
        print(
            f"  {row['id']:<5} {row['name']:<22} {row['username']:<15} {row['role']:<10}"
        )
    print()
    print(f"  Total: {len(rows)} user(s)")
    _pause()


def add_user() -> None:
    """
    Prompt the Admin to create a new user account.

    Steps:
      1. Collect name, role, username, password from Admin.
      2. Validate role locally before calling create_user().
      3. Delegate password hashing + DB insert to create_user() in auth.py.
      4. Display the result.

    Password hashing is intentionally NOT done here — auth.py owns that logic.
    """
    _subheader("Add New User")
    print("  Valid roles: admin, teacher, student")
    print("  (type 'back' at any prompt to cancel)\n")

    name = input("  Full Name    : ").strip()
    if name.lower() == "back":
        return

    role = input("  Role         : ").strip().lower()
    if role == "back":
        return

    # Validate role before wasting time on the rest of the prompts.
    if role not in ("admin", "teacher", "student"):
        print(f"\n  Invalid role '{role}'. Must be admin, teacher, or student.")
        _pause()
        return

    username = input("  Username     : ").strip()
    if username.lower() == "back":
        return

    # Use standard input for password in the admin-creation flow.
    # (getpass is used only in the login screen; here the admin is already
    # authenticated and is setting up another account.)
    password = input("  Password     : ")
    if password.lower() == "back":
        return

    print()

    # Delegate creation + hashing to auth.py — do NOT duplicate that logic.
    success, error = create_user(name, role, username, password)

    if success:
        print("  User created successfully.")
        print(f"  Username: {username}  |  Role: {role}")
    else:
        print(f"  Could not create user: {error}")

    _pause()


def manage_users() -> None:
    """
    Submenu for user management actions.
    Loops until the Admin chooses Back (option 0).
    """
    while True:
        _subheader("Manage Users")
        print("  1. View Users")
        print("  2. Add User")
        print("  0. Back")
        print()
        _line()

        choice = input("  Enter your choice: ").strip()

        if choice == "0":
            return

        elif choice == "1":
            view_users()

        elif choice == "2":
            add_user()

        else:
            print("\n  Invalid choice.")
            _pause()


# ---------------------------------------------------------------------------
# ── CLASS MANAGEMENT ─────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def view_classes() -> None:
    """
    Fetch all classes with their teacher names and display them.

    Uses a JOIN so the Admin sees teacher names, not just numeric IDs.

    SQL used:
        SELECT classes.id, classes.class_name, users.name AS teacher_name
        FROM classes
        JOIN users ON classes.teacher_id = users.id
        ORDER BY classes.class_name
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT classes.id, classes.class_name, users.name AS teacher_name
            FROM classes
            JOIN users ON classes.teacher_id = users.id
            ORDER BY classes.class_name
        """)
        rows = cursor.fetchall()
    finally:
        conn.close()

    _subheader("All Classes")

    if not rows:
        print("  No classes found.")
        _pause()
        return

    print(f"  {'ID':<5} {'Class Name':<20} {'Class Teacher':<25}")
    _line()
    for row in rows:
        print(f"  {row['id']:<5} {row['class_name']:<20} {row['teacher_name']:<25}")
    print()
    print(f"  Total: {len(rows)} class(es)")
    _pause()


def _fetch_teachers(conn: sqlite3.Connection) -> list:
    """
    Return a list of all users with role = 'teacher'.
    Used by add_class() to present a selection list.

    Returns sqlite3.Row objects with at least: id, name, username
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, username FROM users WHERE role = 'teacher' ORDER BY name"
    )
    return cursor.fetchall()


def add_class() -> None:
    """
    Prompt the Admin to create a new class, selecting the teacher from a list.

    Steps:
      1. Ask for the class name.
      2. Query all teachers from the database.
      3. Display them as a numbered list.
      4. Admin picks a number — use the corresponding teacher's real DB id.
      5. INSERT into classes.

    Why not ask the Admin to type a teacher ID?
    → The Admin should never need to know internal database IDs.
    → Showing a list prevents typos and invalid IDs.
    """
    _subheader("Add New Class")
    print("  (type 'back' at any prompt to cancel)\n")

    class_name = input("  Class Name   : ").strip()
    if class_name.lower() == "back":
        return
    if not class_name:
        print("\n  Class name cannot be empty.")
        _pause()
        return

    # Fetch the teacher list inside a temporary connection.
    conn = get_connection()
    try:
        teachers = _fetch_teachers(conn)
    finally:
        conn.close()

    if not teachers:
        print("\n  No teachers found in the system.")
        print("  Please add at least one teacher before creating a class.")
        _pause()
        return

    # Display teachers as a numbered list.
    print()
    print("  Select Class Teacher:")
    _line()
    for i, t in enumerate(teachers, start=1):
        print(f"  {i}. {t['name']}  ({t['username']})")
    _line()

    choice = input("  Enter number: ").strip()
    if choice.lower() == "back":
        return

    # Validate the selection is a valid number within range.
    if not choice.isdigit() or not (1 <= int(choice) <= len(teachers)):
        print(f"\n  Invalid selection. Please enter a number between 1 and {len(teachers)}.")
        _pause()
        return

    # Use the actual database ID — no hard-coding.
    selected_teacher = teachers[int(choice) - 1]
    teacher_id       = selected_teacher["id"]
    teacher_name     = selected_teacher["name"]

    # Insert the new class.
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO classes (class_name, teacher_id) VALUES (?, ?)",
            (class_name, teacher_id)
        )
        conn.commit()
        print()
        print("  Class created successfully.")
        print(f"  Class: {class_name}  |  Teacher: {teacher_name}")

    except sqlite3.IntegrityError:
        # Triggered by the UNIQUE constraint on class_name.
        print()
        print(f"  A class named '{class_name}' already exists.")

    except sqlite3.Error as e:
        print()
        print(f"  Database error: {e}")

    finally:
        conn.close()

    _pause()


def manage_classes() -> None:
    """
    Submenu for class management actions.
    Loops until the Admin chooses Back (option 0).
    """
    while True:
        _subheader("Manage Classes")
        print("  1. View Classes")
        print("  2. Add Class")
        print("  0. Back")
        print()
        _line()

        choice = input("  Enter your choice: ").strip()

        if choice == "0":
            return

        elif choice == "1":
            view_classes()

        elif choice == "2":
            add_class()

        else:
            print("\n  Invalid choice.")
            _pause()


# ---------------------------------------------------------------------------
# ── SUBJECT MANAGEMENT ───────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def view_subjects() -> None:
    """
    Fetch all subjects with their class names and display them.

    Uses a JOIN so the Admin sees class names, not class IDs.

    SQL used:
        SELECT subjects.id, subjects.name, classes.class_name
        FROM subjects
        JOIN classes ON subjects.class_id = classes.id
        ORDER BY classes.class_name, subjects.name
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT subjects.id, subjects.name AS subject_name, classes.class_name
            FROM subjects
            JOIN classes ON subjects.class_id = classes.id
            ORDER BY classes.class_name, subjects.name
        """)
        rows = cursor.fetchall()
    finally:
        conn.close()

    _subheader("All Subjects")

    if not rows:
        print("  No subjects found.")
        _pause()
        return

    print(f"  {'ID':<5} {'Subject Name':<30} {'Class':<20}")
    _line()
    for row in rows:
        print(f"  {row['id']:<5} {row['subject_name']:<30} {row['class_name']:<20}")
    print()
    print(f"  Total: {len(rows)} subject(s)")
    _pause()


def _fetch_classes(conn: sqlite3.Connection) -> list:
    """
    Return a list of all classes.
    Used by add_subject() to present a selection list.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, class_name FROM classes ORDER BY class_name"
    )
    return cursor.fetchall()


def add_subject() -> None:
    """
    Prompt the Admin to add a subject to an existing class.

    Steps:
      1. Ask for the subject name.
      2. Query all classes from the database.
      3. Display them as a numbered list.
      4. Admin picks a class — use its real DB id.
      5. INSERT into subjects.

    Schema rule enforced:
      UNIQUE(name, class_id)
      → same subject name can exist in different classes (e.g., Mathematics in BCA-A and BCA-B)
      → same subject name CANNOT exist twice in the same class
    """
    _subheader("Add New Subject")
    print("  (type 'back' at any prompt to cancel)\n")

    subject_name = input("  Subject Name : ").strip()
    if subject_name.lower() == "back":
        return
    if not subject_name:
        print("\n  Subject name cannot be empty.")
        _pause()
        return

    # Fetch the class list.
    conn = get_connection()
    try:
        classes = _fetch_classes(conn)
    finally:
        conn.close()

    if not classes:
        print("\n  No classes found in the system.")
        print("  Please add at least one class before creating a subject.")
        _pause()
        return

    # Display classes as a numbered list.
    print()
    print("  Select Class for this Subject:")
    _line()
    for i, cls in enumerate(classes, start=1):
        print(f"  {i}. {cls['class_name']}")
    _line()

    choice = input("  Enter number: ").strip()
    if choice.lower() == "back":
        return

    if not choice.isdigit() or not (1 <= int(choice) <= len(classes)):
        print(f"\n  Invalid selection. Please enter a number between 1 and {len(classes)}.")
        _pause()
        return

    selected_class = classes[int(choice) - 1]
    class_id       = selected_class["id"]
    class_name     = selected_class["class_name"]

    # Insert the new subject.
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO subjects (name, class_id) VALUES (?, ?)",
            (subject_name, class_id)
        )
        conn.commit()
        print()
        print("  Subject created successfully.")
        print(f"  Subject: {subject_name}  |  Class: {class_name}")

    except sqlite3.IntegrityError:
        # Triggered by UNIQUE(name, class_id) — duplicate in same class.
        print()
        print(f"  Subject '{subject_name}' already exists in class '{class_name}'.")
        print("  Note: The same subject name is allowed in a different class.")

    except sqlite3.Error as e:
        print()
        print(f"  Database error: {e}")

    finally:
        conn.close()

    _pause()


def manage_subjects() -> None:
    """
    Submenu for subject management actions.
    Loops until the Admin chooses Back (option 0).
    """
    while True:
        _subheader("Manage Subjects")
        print("  1. View Subjects")
        print("  2. Add Subject")
        print("  0. Back")
        print()
        _line()

        choice = input("  Enter your choice: ").strip()

        if choice == "0":
            return

        elif choice == "1":
            view_subjects()

        elif choice == "2":
            add_subject()

        else:
            print("\n  Invalid choice.")
            _pause()


# ---------------------------------------------------------------------------
# ── RESOURCE MANAGEMENT ────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def manage_resources(user) -> None:
    """
    Submenu for Admin resource management actions:
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
        _subheader("Manage Resources")
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
            _subheader("Classroom Resources")
            resources = get_resources()
            if not resources:
                print("  No resources found.")
            else:
                print(f"  {'Code':<10} {'Resource':<24} {'Status':<15} {'Notes'}")
                _line(width=75)
                for r in resources:
                    notes = r["maintenance_notes"] or "-"
                    print(f"  {r['resource_code']:<10} {r['name']:<24} {r['status']:<15} {notes}")
            _pause()

        # ── 2. Book Resource ────────────────────────────────────────────────
        elif choice == "2":
            _subheader("Book a Resource")
            avail = get_available_resources()
            if not avail:
                print("  No resources are currently available for booking.")
                _pause()
                continue

            print("  Available Resources:")
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
            _subheader("Return a Resource")
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
            _subheader("My Booking History")
            bookings = get_user_bookings(user["id"])
            if not bookings:
                print("  You have no booking history.")
            else:
                print(f"  {'Code':<8} {'Resource':<20} {'Booked At':<21} {'Returned At':<21} {'Status'}")
                _line(width=80)
                for b in bookings:
                    ret_str = b["returned_at"] if b["returned_at"] else "-"
                    print(f"  {b['resource_code']:<8} {b['resource_name']:<20} {b['booked_at']:<21} {ret_str:<21} {b['status']}")
            _pause()

        # ── 5. Mark Resource for Maintenance ────────────────────────────────
        elif choice == "5":
            _subheader("Mark Resource for Maintenance")
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
            _subheader("Release Resource from Maintenance")
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
            _subheader("Complete Booking History")
            history = get_booking_history()
            if not history:
                print("  No booking records found in the system.")
            else:
                print(f"  {'Code':<8} {'Resource':<18} {'Booked By':<18} {'Booked At':<20} {'Returned At':<20} {'Status'}")
                _line(width=95)
                for b in history:
                    ret_str = b["returned_at"] if b["returned_at"] else "-"
                    print(f"  {b['resource_code']:<8} {b['resource_name']:<18} {b['user_name']:<18} {b['booked_at']:<20} {ret_str:<20} {b['status']}")
            _pause()

        else:
            print("\n  Invalid choice.")
            _pause()


# ---------------------------------------------------------------------------
# ── ADMIN DASHBOARD ──────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def admin_menu(user) -> None:
    """
    Display the Admin dashboard and route to management submenus.

    Loops until the Admin selects Logout (option 0).
    Returns to main.py login loop when done.

    Parameters:
        user — sqlite3.Row from authenticate_user()
                Fields: user["name"], user["id"], user["role"]
    """
    while True:
        _header("Admin Dashboard")
        print(f"  Welcome, {user['name']}!")
        print(f"  Role   : Administrator")
        _line()
        print()
        print("  1. Manage Users")
        print("  2. Manage Classes")
        print("  3. Manage Subjects")
        print("  7. Manage Resources")
        print()

        # ── Coming in later steps ────────────────────────────────────────────
        print("  --- (Coming soon) ---")
        print("  4. Attendance Reports")
        print("  5. Marks Reports")
        print("  6. Learning Gaps")
        print("  8. Safety Alerts")
        print("  9. Analytics")
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
            manage_users()

        elif choice == "2":
            manage_classes()

        elif choice == "3":
            manage_subjects()

        elif choice == "7":
            manage_resources(user)

        elif choice in ("4", "5", "6", "8", "9"):
            print()
            print("  This feature is not yet implemented.")
            print("  It will be available in a later development step.")
            _pause()

        else:
            print()
            print("  Invalid choice. Please enter a number from the menu.")
            _pause()
