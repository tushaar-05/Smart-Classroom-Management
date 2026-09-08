"""
database.py — SCMS Database Layer
==================================
This module handles two things only:
  1. Creating/returning a connection to the SQLite database.
  2. Initializing the database schema (all 9 tables) on first run.

No business logic lives here. Other modules (attendance.py, marks.py, etc.)
call get_connection() to get a connection, run their queries, and close it.

Database file: data/scms.db  (created automatically if it does not exist)
"""

import sqlite3
import os

# ---------------------------------------------------------------------------
# Path to the database file.
#
# Using os.path.dirname(__file__) makes the path relative to this file
# (database.py) rather than the directory from which the user runs the app.
# This means `python main.py` works correctly whether run from inside the
# SmartClassroom/ folder or from somewhere else on the filesystem.
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH  = os.path.join(DATA_DIR, "scms.db")


def get_connection():
    """
    Open and return a connection to the SCMS SQLite database.

    Every caller is responsible for closing the connection after use.
    Use it like this in other modules:

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ...")
        conn.close()

    Or using Python's context manager (recommended):

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
        # connection is automatically committed and closed here

    Why PRAGMA foreign_keys = ON?
    ------------------------------
    SQLite does NOT enforce foreign keys by default (a legacy design decision).
    We must enable it on every new connection so that, for example, inserting
    a student with a non-existent class_id is correctly rejected.
    """
    conn = sqlite3.connect(DB_PATH)

    # Return rows as sqlite3.Row objects so columns can be accessed by name:
    #   row["username"]  instead of  row[3]
    # This makes the code in other modules much easier to read.
    conn.row_factory = sqlite3.Row

    # Enable foreign-key enforcement for this connection.
    conn.execute("PRAGMA foreign_keys = ON;")

    return conn


def init_db():
    """
    Create the database file and all 9 tables if they do not already exist.

    First run behaviour:
        - Creates the data/ directory if missing.
        - Creates data/scms.db if missing.
        - Executes all CREATE TABLE IF NOT EXISTS statements.
        - Commits and closes.
        After this call, a fully structured (but empty) database is ready.

    Subsequent runs:
        - IF NOT EXISTS means SQLite skips tables that already exist.
        - Existing data is completely untouched.
        - Safe to call every time the application starts.
    """
    # Create the data/ directory if it does not exist yet.
    os.makedirs(DATA_DIR, exist_ok=True)

    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------------------------------------------------
    # Create tables in dependency order:
    #   users → classes → subjects → students
    #                             → attendance (needs students + subjects)
    #                             → marks      (needs students + subjects)
    #   resources → bookings (needs resources + users)
    #   alerts   (needs users)
    #
    # SQLite requires that a referenced table already exist when the
    # foreign key is defined, so the order below matters.
    # -------------------------------------------------------------------

    # 1. users -----------------------------------------------------------
    # Every person who can log in.  Referenced by almost every other table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            role          TEXT    NOT NULL
                          CHECK(role IN ('admin', 'teacher', 'student')),
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            password_salt TEXT    NOT NULL
        )
    """)

    # 2. classes ---------------------------------------------------------
    # A classroom section (e.g. "CS-A 2nd Year").
    # Each class has one class teacher.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name   TEXT    NOT NULL UNIQUE,
            teacher_id   INTEGER NOT NULL
                         REFERENCES users(id)
        )
    """)

    # 3. subjects --------------------------------------------------------
    # Canonical list of subjects for each class.
    # Attendance and marks reference subject_id (not a raw string) to
    # prevent typos from corrupting percentage calculations.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            class_id INTEGER NOT NULL
                     REFERENCES classes(id),
            UNIQUE (name, class_id)
        )
    """)

    # 4. students --------------------------------------------------------
    # Student-specific profile data that extends the users table.
    # A student always belongs to one class.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL UNIQUE
                        REFERENCES users(id),
            roll_number TEXT    NOT NULL UNIQUE,
            class_id    INTEGER NOT NULL
                        REFERENCES classes(id)
        )
    """)

    # 5. attendance ------------------------------------------------------
    # One row per student per subject per date.
    # UNIQUE constraint prevents marking the same student twice on one day
    # for the same subject.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id),
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            date       TEXT    NOT NULL,
            status     TEXT    NOT NULL
                       CHECK(status IN ('Present', 'Absent')),
            UNIQUE (student_id, subject_id, date)
        )
    """)

    # 6. marks -----------------------------------------------------------
    # One row per student per subject per test.
    # Multiple tests per subject per student are supported so averages
    # can be computed across all tests.
    # CHECK constraints ensure marks are logically valid.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id     INTEGER NOT NULL REFERENCES students(id),
            subject_id     INTEGER NOT NULL REFERENCES subjects(id),
            test_name      TEXT    NOT NULL,
            marks_obtained REAL    NOT NULL CHECK(marks_obtained >= 0),
            max_marks      REAL    NOT NULL CHECK(max_marks > 0),
            date           TEXT    NOT NULL,
            CHECK (marks_obtained <= max_marks)
        )
    """)

    # 7. resources -------------------------------------------------------
    # Classroom equipment inventory.
    # Status drives the booking workflow:
    #   Available → In Use  (when booked)
    #   In Use → Available  (when returned)
    #   Available → Maintenance  (flagged by admin)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_code     TEXT    NOT NULL UNIQUE,
            name              TEXT    NOT NULL,
            status            TEXT    NOT NULL DEFAULT 'Available'
                              CHECK(status IN ('Available', 'In Use', 'Maintenance')),
            maintenance_notes TEXT
        )
    """)

    # 8. bookings --------------------------------------------------------
    # History of every resource booking.
    # returned_at IS NULL means the resource is still checked out.
    # The application (resources.py) checks for an open booking before
    # allowing a new one — no database trigger needed.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL REFERENCES resources(id),
            booked_by   INTEGER NOT NULL REFERENCES users(id),
            booked_at   TEXT    NOT NULL,
            returned_at TEXT
        )
    """)

    # 9. alerts ----------------------------------------------------------
    # Safety/security incidents.
    # resolved_by and resolved_at are NULL until an admin resolves the alert.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type  TEXT    NOT NULL
                        CHECK(alert_type IN
                              ('Fire', 'Unauthorized Access', 'Medical', 'Other')),
            location    TEXT    NOT NULL,
            description TEXT,
            status      TEXT    NOT NULL DEFAULT 'Active'
                        CHECK(status IN ('Active', 'Resolved')),
            created_by  INTEGER NOT NULL REFERENCES users(id),
            created_at  TEXT    NOT NULL,
            resolved_by INTEGER REFERENCES users(id),
            resolved_at TEXT
        )
    """)

    # Save all table-creation changes to the database file.
    conn.commit()
    conn.close()

    print(f"Database initialized at: {DB_PATH}")
