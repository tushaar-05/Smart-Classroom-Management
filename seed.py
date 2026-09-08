"""
seed.py — SCMS Demo Database Seeder
=====================================
Populates data/scms.db with realistic fictional demo data for the
Smart Classroom Management System prototype.

Usage:
    python3 seed.py

What this script does:
    1. Initializes the database (creates tables if missing).
    2. Clears all existing demo data (full table wipe in safe order).
    3. Inserts all demo records in correct foreign-key dependency order.
    4. Commits everything in a single transaction (rolls back on error).
    5. Prints a summary with login credentials.

IMPORTANT:
    - This script is for demo/development use only.
    - Do NOT import this from main.py.
    - Running it resets ALL data in the database.
    - Passwords are hashed — plain-text passwords are NEVER stored.

Demo insertion order (foreign-key dependency order):
    users → classes → subjects → students
         → attendance, marks
    users → resources → bookings
    users → alerts

Standard-library only. No external packages required.
"""

import sqlite3
import sys

from database import get_connection, init_db
from modules.auth import hash_password, authenticate_user


# ---------------------------------------------------------------------------
# Demo data definitions
# ---------------------------------------------------------------------------

# ── Users ───────────────────────────────────────────────────────────────────

# Format: (name, role, username, plain_password)
# Passwords are hashed before storage — these plain texts are printed in the
# summary and then discarded. They are NEVER written to the database.
DEMO_USERS = [
    # Admin
    ("Arun Kumar",      "admin",   "admin",     "Admin@123"),

    # Teachers
    ("Ms. Priya Nair",  "teacher", "priya_t",   "Teacher@1"),
    ("Mr. Rahul Joshi", "teacher", "rahul_t",   "Teacher@2"),

    # Students — BCA-A (will be assigned class_id dynamically)
    ("Ananya Sharma",   "student", "ananya_s",  "Pass@1234"),
    ("Rohit Mehta",     "student", "rohit_s",   "Pass@1234"),
    ("Divya Pillai",    "student", "divya_s",   "Pass@1234"),
    ("Karthik Reddy",   "student", "karthik_s", "Pass@1234"),
    ("Sneha Gupta",     "student", "sneha_s",   "Pass@1234"),

    # Students — BCA-B (will be assigned class_id dynamically)
    ("Arjun Singh",     "student", "arjun_s",   "Pass@1234"),
    ("Meena Iyer",      "student", "meena_s",   "Pass@1234"),
    ("Vikas Tiwari",    "student", "vikas_s",   "Pass@1234"),
    ("Pooja Bansal",    "student", "pooja_s",   "Pass@1234"),
]

# ── Classes ─────────────────────────────────────────────────────────────────
# Format: (class_name, teacher_username)
# teacher_username is resolved to a user ID at runtime — no hard-coding.
DEMO_CLASSES = [
    ("BCA-A", "priya_t"),
    ("BCA-B", "rahul_t"),
]

# ── Subjects ─────────────────────────────────────────────────────────────────
# Format: (subject_name, class_name)
# class_name is resolved to a class ID at runtime.
DEMO_SUBJECTS = [
    # BCA-A subjects
    ("Mathematics",          "BCA-A"),
    ("Programming in Python","BCA-A"),
    ("Database Management",  "BCA-A"),
    # BCA-B subjects
    ("Mathematics",          "BCA-B"),    # same name in a different class — allowed
    ("Web Technologies",     "BCA-B"),
    ("Operating Systems",    "BCA-B"),
]

# ── Student → Class assignment ───────────────────────────────────────────────
# Format: (username, roll_number, class_name)
DEMO_STUDENTS = [
    # BCA-A
    ("ananya_s",  "BCA-A-001", "BCA-A"),
    ("rohit_s",   "BCA-A-002", "BCA-A"),
    ("divya_s",   "BCA-A-003", "BCA-A"),
    ("karthik_s", "BCA-A-004", "BCA-A"),
    ("sneha_s",   "BCA-A-005", "BCA-A"),
    # BCA-B
    ("arjun_s",   "BCA-B-001", "BCA-B"),
    ("meena_s",   "BCA-B-002", "BCA-B"),
    ("vikas_s",   "BCA-B-003", "BCA-B"),
    ("pooja_s",   "BCA-B-004", "BCA-B"),
]

# ── Attendance ───────────────────────────────────────────────────────────────
# 18 school days across Jan–Feb 2024.
ATTENDANCE_DATES = [
    "2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12",
    "2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19",
    "2024-01-22", "2024-01-23", "2024-01-24", "2024-01-25", "2024-01-26",
    "2024-01-29", "2024-01-30", "2024-01-31",
]

# Per-student attendance pattern:
# 0 = Absent, 1 = Present
# The list maps to ATTENDANCE_DATES in order.
# Rohit (BCA-A-002) has only 10/18 = 55.6% attendance → below 75% threshold
# Pooja (BCA-B-004) has only 12/18 = 66.7% attendance → below 75% threshold
# All others are above 75%.
ATTENDANCE_PATTERNS = {
    #  username   :  pattern for all 18 dates
    "ananya_s"  : [1,1,1,1,1, 1,1,0,1,1, 1,1,1,0,1, 1,1,1],   # 16/18 = 89%
    "rohit_s"   : [1,0,1,0,1, 0,1,0,1,0, 1,0,1,0,1, 0,1,0],   # 9/18  = 50% ← LOW
    "divya_s"   : [1,1,1,0,1, 1,1,1,1,1, 0,1,1,1,1, 1,1,1],   # 16/18 = 89%
    "karthik_s" : [1,1,0,1,1, 1,0,1,1,1, 1,1,0,1,1, 1,1,1],   # 15/18 = 83%
    "sneha_s"   : [1,1,1,1,1, 1,1,1,0,1, 1,1,1,1,1, 1,0,1],   # 16/18 = 89%
    "arjun_s"   : [1,1,1,1,1, 0,1,1,1,1, 1,1,1,1,1, 1,1,1],   # 17/18 = 94%
    "meena_s"   : [0,1,1,1,1, 1,1,1,1,0, 1,1,1,1,1, 1,1,1],   # 16/18 = 89%
    "vikas_s"   : [1,1,1,1,0, 1,1,1,1,1, 1,0,1,1,1, 1,1,1],   # 16/18 = 89%
    "pooja_s"   : [1,0,1,0,1, 0,0,1,0,1, 1,0,1,0,1, 0,1,0],   # 9/18  = 50% ← LOW
}

# ── Marks ────────────────────────────────────────────────────────────────────
# Format: (student_username, subject_name, test_name, marks_obtained, max_marks, date)
# Marks are subject to: marks_obtained >= 0, max_marks > 0, marks_obtained <= max_marks
#
# Rohit (BCA-A) has very low marks in Mathematics → avg < 50% (learning gap)
# Pooja (BCA-B) has very low marks in Mathematics → avg < 50% (learning gap)
DEMO_MARKS = [
    # ── BCA-A students ──────────────────────────────────────────────────────
    # Ananya — good performance
    ("ananya_s",  "Mathematics",           "Unit Test 1",   38, 50, "2024-01-20"),
    ("ananya_s",  "Mathematics",           "Unit Test 2",   42, 50, "2024-02-10"),
    ("ananya_s",  "Mathematics",           "Mid-Term",      72, 100,"2024-02-20"),
    ("ananya_s",  "Programming in Python", "Unit Test 1",   44, 50, "2024-01-20"),
    ("ananya_s",  "Programming in Python", "Unit Test 2",   46, 50, "2024-02-10"),
    ("ananya_s",  "Programming in Python", "Mid-Term",      80, 100,"2024-02-20"),
    ("ananya_s",  "Database Management",   "Unit Test 1",   40, 50, "2024-01-20"),
    ("ananya_s",  "Database Management",   "Unit Test 2",   38, 50, "2024-02-10"),
    ("ananya_s",  "Database Management",   "Mid-Term",      70, 100,"2024-02-20"),

    # Rohit — LOW marks in Mathematics (avg ~26%), okay in others
    ("rohit_s",   "Mathematics",           "Unit Test 1",   12, 50, "2024-01-20"),
    ("rohit_s",   "Mathematics",           "Unit Test 2",   14, 50, "2024-02-10"),
    ("rohit_s",   "Mathematics",           "Mid-Term",      26, 100,"2024-02-20"),
    ("rohit_s",   "Programming in Python", "Unit Test 1",   35, 50, "2024-01-20"),
    ("rohit_s",   "Programming in Python", "Unit Test 2",   38, 50, "2024-02-10"),
    ("rohit_s",   "Programming in Python", "Mid-Term",      62, 100,"2024-02-20"),
    ("rohit_s",   "Database Management",   "Unit Test 1",   30, 50, "2024-01-20"),
    ("rohit_s",   "Database Management",   "Unit Test 2",   32, 50, "2024-02-10"),
    ("rohit_s",   "Database Management",   "Mid-Term",      55, 100,"2024-02-20"),

    # Divya — good all round
    ("divya_s",   "Mathematics",           "Unit Test 1",   40, 50, "2024-01-20"),
    ("divya_s",   "Mathematics",           "Unit Test 2",   44, 50, "2024-02-10"),
    ("divya_s",   "Mathematics",           "Mid-Term",      78, 100,"2024-02-20"),
    ("divya_s",   "Programming in Python", "Unit Test 1",   47, 50, "2024-01-20"),
    ("divya_s",   "Programming in Python", "Unit Test 2",   48, 50, "2024-02-10"),
    ("divya_s",   "Programming in Python", "Mid-Term",      88, 100,"2024-02-20"),
    ("divya_s",   "Database Management",   "Unit Test 1",   42, 50, "2024-01-20"),
    ("divya_s",   "Database Management",   "Unit Test 2",   40, 50, "2024-02-10"),
    ("divya_s",   "Database Management",   "Mid-Term",      75, 100,"2024-02-20"),

    # Karthik — average
    ("karthik_s", "Mathematics",           "Unit Test 1",   28, 50, "2024-01-20"),
    ("karthik_s", "Mathematics",           "Unit Test 2",   30, 50, "2024-02-10"),
    ("karthik_s", "Mathematics",           "Mid-Term",      58, 100,"2024-02-20"),
    ("karthik_s", "Programming in Python", "Unit Test 1",   33, 50, "2024-01-20"),
    ("karthik_s", "Programming in Python", "Unit Test 2",   36, 50, "2024-02-10"),
    ("karthik_s", "Programming in Python", "Mid-Term",      65, 100,"2024-02-20"),
    ("karthik_s", "Database Management",   "Unit Test 1",   35, 50, "2024-01-20"),
    ("karthik_s", "Database Management",   "Unit Test 2",   34, 50, "2024-02-10"),
    ("karthik_s", "Database Management",   "Mid-Term",      60, 100,"2024-02-20"),

    # Sneha — good
    ("sneha_s",   "Mathematics",           "Unit Test 1",   43, 50, "2024-01-20"),
    ("sneha_s",   "Mathematics",           "Unit Test 2",   45, 50, "2024-02-10"),
    ("sneha_s",   "Mathematics",           "Mid-Term",      82, 100,"2024-02-20"),
    ("sneha_s",   "Programming in Python", "Unit Test 1",   46, 50, "2024-01-20"),
    ("sneha_s",   "Programming in Python", "Unit Test 2",   48, 50, "2024-02-10"),
    ("sneha_s",   "Programming in Python", "Mid-Term",      85, 100,"2024-02-20"),
    ("sneha_s",   "Database Management",   "Unit Test 1",   39, 50, "2024-01-20"),
    ("sneha_s",   "Database Management",   "Unit Test 2",   41, 50, "2024-02-10"),
    ("sneha_s",   "Database Management",   "Mid-Term",      72, 100,"2024-02-20"),

    # ── BCA-B students ──────────────────────────────────────────────────────
    # Arjun — good
    ("arjun_s",   "Mathematics",           "Unit Test 1",   40, 50, "2024-01-20"),
    ("arjun_s",   "Mathematics",           "Unit Test 2",   42, 50, "2024-02-10"),
    ("arjun_s",   "Mathematics",           "Mid-Term",      75, 100,"2024-02-20"),
    ("arjun_s",   "Web Technologies",      "Unit Test 1",   44, 50, "2024-01-20"),
    ("arjun_s",   "Web Technologies",      "Unit Test 2",   46, 50, "2024-02-10"),
    ("arjun_s",   "Web Technologies",      "Mid-Term",      82, 100,"2024-02-20"),
    ("arjun_s",   "Operating Systems",     "Unit Test 1",   38, 50, "2024-01-20"),
    ("arjun_s",   "Operating Systems",     "Unit Test 2",   40, 50, "2024-02-10"),
    ("arjun_s",   "Operating Systems",     "Mid-Term",      70, 100,"2024-02-20"),

    # Meena — good
    ("meena_s",   "Mathematics",           "Unit Test 1",   39, 50, "2024-01-20"),
    ("meena_s",   "Mathematics",           "Unit Test 2",   41, 50, "2024-02-10"),
    ("meena_s",   "Mathematics",           "Mid-Term",      74, 100,"2024-02-20"),
    ("meena_s",   "Web Technologies",      "Unit Test 1",   43, 50, "2024-01-20"),
    ("meena_s",   "Web Technologies",      "Unit Test 2",   45, 50, "2024-02-10"),
    ("meena_s",   "Web Technologies",      "Mid-Term",      80, 100,"2024-02-20"),
    ("meena_s",   "Operating Systems",     "Unit Test 1",   37, 50, "2024-01-20"),
    ("meena_s",   "Operating Systems",     "Unit Test 2",   39, 50, "2024-02-10"),
    ("meena_s",   "Operating Systems",     "Mid-Term",      68, 100,"2024-02-20"),

    # Vikas — average
    ("vikas_s",   "Mathematics",           "Unit Test 1",   29, 50, "2024-01-20"),
    ("vikas_s",   "Mathematics",           "Unit Test 2",   31, 50, "2024-02-10"),
    ("vikas_s",   "Mathematics",           "Mid-Term",      60, 100,"2024-02-20"),
    ("vikas_s",   "Web Technologies",      "Unit Test 1",   34, 50, "2024-01-20"),
    ("vikas_s",   "Web Technologies",      "Unit Test 2",   36, 50, "2024-02-10"),
    ("vikas_s",   "Web Technologies",      "Mid-Term",      65, 100,"2024-02-20"),
    ("vikas_s",   "Operating Systems",     "Unit Test 1",   33, 50, "2024-01-20"),
    ("vikas_s",   "Operating Systems",     "Unit Test 2",   35, 50, "2024-02-10"),
    ("vikas_s",   "Operating Systems",     "Mid-Term",      62, 100,"2024-02-20"),

    # Pooja — LOW marks in Mathematics (avg ~26%), others are okay
    ("pooja_s",   "Mathematics",           "Unit Test 1",   11, 50, "2024-01-20"),
    ("pooja_s",   "Mathematics",           "Unit Test 2",   13, 50, "2024-02-10"),
    ("pooja_s",   "Mathematics",           "Mid-Term",      24, 100,"2024-02-20"),
    ("pooja_s",   "Web Technologies",      "Unit Test 1",   36, 50, "2024-01-20"),
    ("pooja_s",   "Web Technologies",      "Unit Test 2",   38, 50, "2024-02-10"),
    ("pooja_s",   "Web Technologies",      "Mid-Term",      68, 100,"2024-02-20"),
    ("pooja_s",   "Operating Systems",     "Unit Test 1",   30, 50, "2024-01-20"),
    ("pooja_s",   "Operating Systems",     "Unit Test 2",   32, 50, "2024-02-10"),
    ("pooja_s",   "Operating Systems",     "Mid-Term",      56, 100,"2024-02-20"),
]

# ── Resources ────────────────────────────────────────────────────────────────
# Format: (resource_code, name, status, maintenance_notes)
DEMO_RESOURCES = [
    ("R01", "Projector",       "Available",   None),
    ("R02", "Smart Board",     "In Use",      None),
    ("R03", "Desktop Computer","Available",   None),
    ("R04", "Speaker System",  "Maintenance", "Speaker crackle — sent for repair on 2024-01-25"),
    ("R05", "HDMI Cable Kit",  "Available",   None),
]

# ── Bookings ─────────────────────────────────────────────────────────────────
# Format: (resource_code, booked_by_username, booked_at, returned_at)
# returned_at = None means the booking is still active.
DEMO_BOOKINGS = [
    # Returned bookings (historical)
    ("R01", "priya_t", "2024-01-08 09:00:00", "2024-01-08 11:00:00"),
    ("R01", "rahul_t", "2024-01-10 10:00:00", "2024-01-10 12:00:00"),
    ("R03", "priya_t", "2024-01-15 09:30:00", "2024-01-15 13:00:00"),
    ("R05", "rahul_t", "2024-01-17 11:00:00", "2024-01-17 13:00:00"),
    ("R01", "priya_t", "2024-01-22 09:00:00", "2024-01-22 11:30:00"),
    # Active booking — Smart Board still checked out
    ("R02", "rahul_t", "2024-01-31 09:00:00", None),
]

# ── Safety Alerts ─────────────────────────────────────────────────────────────
# Format: (alert_type, location, description, status,
#          created_by_username, created_at, resolved_by_username, resolved_at)
# resolved_by_username = None for Active alerts.
DEMO_ALERTS = [
    # Resolved alerts
    (
        "Fire",
        "Room 204",
        "Small fire reported near the electrical panel. Students evacuated. False alarm confirmed.",
        "Resolved",
        "priya_t", "2024-01-10 10:15:00",
        "admin",   "2024-01-10 10:45:00",
    ),
    (
        "Medical",
        "Room 101",
        "Student reported dizziness. First aid administered. Parents notified.",
        "Resolved",
        "rahul_t", "2024-01-18 14:00:00",
        "admin",   "2024-01-18 14:30:00",
    ),
    (
        "Unauthorized Access",
        "Server Room",
        "Unidentified person found near server room door. Security team alerted.",
        "Resolved",
        "priya_t", "2024-01-24 16:00:00",
        "admin",   "2024-01-24 16:20:00",
    ),
    # Active alerts (not yet resolved)
    (
        "Other",
        "Corridor B",
        "Water leakage from ceiling. Maintenance team informed.",
        "Active",
        "rahul_t", "2024-01-30 11:00:00",
        None, None,
    ),
    (
        "Medical",
        "Room 105",
        "Student reported severe allergic reaction. Ambulance called.",
        "Active",
        "priya_t", "2024-01-31 13:30:00",
        None, None,
    ),
]


# ---------------------------------------------------------------------------
# Reset helper
# ---------------------------------------------------------------------------

def clear_all_data(conn: sqlite3.Connection) -> None:
    """
    Delete all rows from all 9 tables in reverse dependency order.

    Reverse order is required so that rows referencing other tables
    are deleted before the rows they reference. With foreign keys ON,
    SQLite would reject deletes that leave orphan references behind.

    Dependency order (top → needs bottom):
        attendance, marks → students → subjects → classes → users
        bookings          → resources
        bookings          → users
        alerts            → users

    Reverse = delete in bottom-up order:
        attendance, marks, bookings, alerts
        → students
        → subjects
        → classes
        → resources
        → users

    We use DELETE FROM rather than DROP TABLE + recreate, so the schema
    (table structures, constraints) is preserved — only the rows are removed.
    """
    cursor = conn.cursor()

    # Delete leaf tables first (they reference other tables).
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM marks")
    cursor.execute("DELETE FROM bookings")
    cursor.execute("DELETE FROM alerts")

    # Now delete mid-level tables.
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM subjects")

    # Now delete top-level tables that were referenced above.
    cursor.execute("DELETE FROM classes")
    cursor.execute("DELETE FROM resources")

    # Finally delete users (referenced by almost everything).
    cursor.execute("DELETE FROM users")

    # Reset the AUTOINCREMENT counters so IDs start from 1 again.
    # sqlite_sequence is the internal table SQLite uses to track these.
    cursor.execute("DELETE FROM sqlite_sequence")


# ---------------------------------------------------------------------------
# Individual seed functions
# ---------------------------------------------------------------------------

def seed_users(conn: sqlite3.Connection) -> dict[str, int]:
    """
    Insert all demo users and return a mapping of username → user_id.

    Passwords are hashed using hash_password() (same function as normal
    user creation). Plain-text passwords are only used here in source code
    for seeding — they are never written to the database.

    Returns:
        { "admin": 1, "priya_t": 2, ... }
    """
    username_to_id = {}
    cursor = conn.cursor()

    for name, role, username, password in DEMO_USERS:
        # Hash the password — identical to how auth.create_user() does it.
        ph, ps = hash_password(password)

        cursor.execute(
            """
            INSERT INTO users (name, role, username, password_hash, password_salt)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, role, username, ph, ps)
        )
        # Retrieve the auto-assigned ID for this user.
        # lastrowid gives the rowid of the most recently inserted row.
        user_id = cursor.lastrowid
        username_to_id[username] = user_id

    return username_to_id


def seed_classes(
    conn: sqlite3.Connection,
    username_to_id: dict[str, int]
) -> dict[str, int]:
    """
    Insert demo classes and return a mapping of class_name → class_id.

    Uses teacher IDs from username_to_id rather than hard-coding numbers.
    """
    class_to_id = {}
    cursor = conn.cursor()

    for class_name, teacher_username in DEMO_CLASSES:
        teacher_id = username_to_id[teacher_username]
        cursor.execute(
            "INSERT INTO classes (class_name, teacher_id) VALUES (?, ?)",
            (class_name, teacher_id)
        )
        class_to_id[class_name] = cursor.lastrowid

    return class_to_id


def seed_subjects(
    conn: sqlite3.Connection,
    class_to_id: dict[str, int]
) -> dict[tuple[str, str], int]:
    """
    Insert demo subjects and return a mapping of (subject_name, class_name) → subject_id.

    The key is a (name, class_name) tuple because the same subject name
    can appear in different classes (e.g., "Mathematics" in both BCA-A and BCA-B).
    """
    subject_key_to_id: dict[tuple[str, str], int] = {}
    cursor = conn.cursor()

    for subject_name, class_name in DEMO_SUBJECTS:
        class_id = class_to_id[class_name]
        cursor.execute(
            "INSERT INTO subjects (name, class_id) VALUES (?, ?)",
            (subject_name, class_id)
        )
        subject_key_to_id[(subject_name, class_name)] = cursor.lastrowid

    return subject_key_to_id


def seed_students(
    conn: sqlite3.Connection,
    username_to_id: dict[str, int],
    class_to_id: dict[str, int]
) -> dict[str, int]:
    """
    Insert demo student profiles and return a mapping of username → student_id.

    Each student record links a users row (for login) to a classes row
    (for which section they belong to).
    """
    username_to_student_id = {}
    cursor = conn.cursor()

    for username, roll_number, class_name in DEMO_STUDENTS:
        user_id  = username_to_id[username]
        class_id = class_to_id[class_name]
        cursor.execute(
            "INSERT INTO students (user_id, roll_number, class_id) VALUES (?, ?, ?)",
            (user_id, roll_number, class_id)
        )
        username_to_student_id[username] = cursor.lastrowid

    return username_to_student_id


def seed_attendance(
    conn: sqlite3.Connection,
    username_to_student_id: dict[str, int],
    subject_key_to_id: dict[tuple[str, str], int],
    class_to_id: dict[str, int]
) -> int:
    """
    Insert attendance records for all students across all their subjects.

    Each student attends all subjects of their own class on each school day.
    Attendance status is determined by the pre-defined ATTENDANCE_PATTERNS.

    Returns the total number of attendance records inserted.
    """
    cursor = conn.cursor()
    count = 0

    # Build a mapping of student_username → class_name for easy lookup.
    student_class = {uname: cls for uname, _, cls in DEMO_STUDENTS}

    # Build a mapping of class_name → list of subject names in that class.
    class_subjects: dict[str, list[str]] = {}
    for subj_name, cls_name in DEMO_SUBJECTS:
        class_subjects.setdefault(cls_name, []).append(subj_name)

    for username, pattern in ATTENDANCE_PATTERNS.items():
        student_id = username_to_student_id[username]
        class_name = student_class[username]
        subjects_in_class = class_subjects[class_name]

        for subject_name in subjects_in_class:
            subject_id = subject_key_to_id[(subject_name, class_name)]

            for i, date in enumerate(ATTENDANCE_DATES):
                status = "Present" if pattern[i] == 1 else "Absent"
                cursor.execute(
                    """
                    INSERT INTO attendance (student_id, subject_id, date, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    (student_id, subject_id, date, status)
                )
                count += 1

    return count


def seed_marks(
    conn: sqlite3.Connection,
    username_to_student_id: dict[str, int],
    subject_key_to_id: dict[tuple[str, str], int]
) -> int:
    """
    Insert marks records.

    Each entry in DEMO_MARKS specifies a student username and subject name.
    The subject is looked up using the student's class, derived from
    DEMO_STUDENTS.

    Returns the total number of marks records inserted.
    """
    cursor = conn.cursor()
    count = 0

    # Map username → class_name for subject resolution.
    student_class = {uname: cls for uname, _, cls in DEMO_STUDENTS}

    for (
        username, subject_name, test_name,
        marks_obtained, max_marks, date
    ) in DEMO_MARKS:
        student_id = username_to_student_id[username]
        class_name = student_class[username]
        subject_id = subject_key_to_id[(subject_name, class_name)]

        cursor.execute(
            """
            INSERT INTO marks
                (student_id, subject_id, test_name, marks_obtained, max_marks, date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (student_id, subject_id, test_name, marks_obtained, max_marks, date)
        )
        count += 1

    return count


def seed_resources(conn: sqlite3.Connection) -> dict[str, int]:
    """
    Insert classroom resources and return a mapping of resource_code → resource_id.
    """
    code_to_id = {}
    cursor = conn.cursor()

    for code, name, status, notes in DEMO_RESOURCES:
        cursor.execute(
            """
            INSERT INTO resources (resource_code, name, status, maintenance_notes)
            VALUES (?, ?, ?, ?)
            """,
            (code, name, status, notes)
        )
        code_to_id[code] = cursor.lastrowid

    return code_to_id


def seed_bookings(
    conn: sqlite3.Connection,
    code_to_id: dict[str, int],
    username_to_id: dict[str, int]
) -> int:
    """
    Insert resource booking records.

    returned_at = None produces a NULL in the database, representing
    an active (not yet returned) booking.

    Returns the total number of booking records inserted.
    """
    cursor = conn.cursor()
    count = 0

    for resource_code, booked_by_username, booked_at, returned_at in DEMO_BOOKINGS:
        resource_id = code_to_id[resource_code]
        booked_by   = username_to_id[booked_by_username]
        cursor.execute(
            """
            INSERT INTO bookings (resource_id, booked_by, booked_at, returned_at)
            VALUES (?, ?, ?, ?)
            """,
            (resource_id, booked_by, booked_at, returned_at)
        )
        count += 1

    return count


def seed_alerts(
    conn: sqlite3.Connection,
    username_to_id: dict[str, int]
) -> int:
    """
    Insert safety/security alert records.

    For Active alerts, resolved_by and resolved_at are NULL.
    For Resolved alerts, both fields have valid values.

    Returns the total number of alert records inserted.
    """
    cursor = conn.cursor()
    count = 0

    for (
        alert_type, location, description, status,
        created_by_username, created_at,
        resolved_by_username, resolved_at
    ) in DEMO_ALERTS:
        created_by  = username_to_id[created_by_username]
        resolved_by = username_to_id.get(resolved_by_username) if resolved_by_username else None

        cursor.execute(
            """
            INSERT INTO alerts
                (alert_type, location, description, status,
                 created_by, created_at, resolved_by, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (alert_type, location, description, status,
             created_by, created_at, resolved_by, resolved_at)
        )
        count += 1

    return count


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def seed():
    """
    Run the full seed operation inside a single database transaction.

    If any step fails, the entire transaction is rolled back so the
    database is never left in a half-seeded state.
    """
    # Ensure the database and schema exist before seeding.
    init_db()

    conn = get_connection()

    # Print header
    print()
    print("=" * 44)
    print("  SCMS Demo Database Seed")
    print("=" * 44)
    print()

    try:
        # ── Step 1: Wipe all existing data ───────────────────────────────────
        print("  Clearing existing data...")
        clear_all_data(conn)
        print("  Database reset successfully.")
        print()

        # ── Step 2: Insert users ─────────────────────────────────────────────
        print("  Seeding users...", end=" ")
        username_to_id = seed_users(conn)
        print(f"{len(username_to_id)} records.")

        # ── Step 3: Insert classes ───────────────────────────────────────────
        print("  Seeding classes...", end=" ")
        class_to_id = seed_classes(conn, username_to_id)
        print(f"{len(class_to_id)} records.")

        # ── Step 4: Insert subjects ──────────────────────────────────────────
        print("  Seeding subjects...", end=" ")
        subject_key_to_id = seed_subjects(conn, class_to_id)
        print(f"{len(subject_key_to_id)} records.")

        # ── Step 5: Insert students ──────────────────────────────────────────
        print("  Seeding students...", end=" ")
        username_to_student_id = seed_students(conn, username_to_id, class_to_id)
        print(f"{len(username_to_student_id)} records.")

        # ── Step 6: Insert attendance ────────────────────────────────────────
        print("  Seeding attendance...", end=" ")
        att_count = seed_attendance(
            conn, username_to_student_id, subject_key_to_id, class_to_id
        )
        print(f"{att_count} records.")

        # ── Step 7: Insert marks ─────────────────────────────────────────────
        print("  Seeding marks...", end=" ")
        marks_count = seed_marks(conn, username_to_student_id, subject_key_to_id)
        print(f"{marks_count} records.")

        # ── Step 8: Insert resources ─────────────────────────────────────────
        print("  Seeding resources...", end=" ")
        code_to_id = seed_resources(conn)
        print(f"{len(code_to_id)} records.")

        # ── Step 9: Insert bookings ──────────────────────────────────────────
        print("  Seeding bookings...", end=" ")
        booking_count = seed_bookings(conn, code_to_id, username_to_id)
        print(f"{booking_count} records.")

        # ── Step 10: Insert alerts ───────────────────────────────────────────
        print("  Seeding alerts...", end=" ")
        alert_count = seed_alerts(conn, username_to_id)
        print(f"{alert_count} records.")

        # ── Commit everything in one transaction ─────────────────────────────
        conn.commit()

        # ── Summary ──────────────────────────────────────────────────────────
        print()
        print("-" * 44)
        print("  Summary")
        print("-" * 44)
        print(f"  Users        : {len(username_to_id)}")
        print(f"  Classes      : {len(class_to_id)}")
        print(f"  Subjects     : {len(subject_key_to_id)}")
        print(f"  Students     : {len(username_to_student_id)}")
        print(f"  Attendance   : {att_count}")
        print(f"  Marks        : {marks_count}")
        print(f"  Resources    : {len(code_to_id)}")
        print(f"  Bookings     : {booking_count}")
        print(f"  Alerts       : {alert_count}")
        print()
        print("-" * 44)
        print("  Demo Login Accounts")
        print("-" * 44)
        print("  Role      Username      Password")
        print("  --------  ------------  ----------")
        print("  Admin     admin         Admin@123")
        print("  Teacher   priya_t       Teacher@1")
        print("  Teacher   rahul_t       Teacher@2")
        print("  Student   ananya_s      Pass@1234")
        print("  Student   rohit_s       Pass@1234  ← low attendance + low marks")
        print("  Student   pooja_s       Pass@1234  ← low attendance + low marks")
        print("  (all other students use Pass@1234)")
        print()
        print("  Note: Passwords are hashed in the database.")
        print("        Plain-text passwords are shown here for demo only.")
        print()
        print("=" * 44)
        print("  Seed completed successfully.")
        print("=" * 44)
        print()
        print("  Run the application with:  python3 main.py")
        print()

    except Exception as e:
        # Something went wrong — roll back every change made in this session.
        # This prevents a half-seeded database.
        conn.rollback()
        print()
        print(f"  ERROR: Seed failed — {e}")
        print("  All changes have been rolled back.")
        print()
        sys.exit(1)

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    seed()
