# Database Schema Reference — SCMS

Smart Classroom Management System · SQLite · College Prototype

This document is the authoritative reference for the SCMS database. It defines every table, column, constraint, and relationship. The SQL at the bottom of this file is the single source of truth that `database.py` will use to initialise the database.

---

## Overview

The SCMS database is a single SQLite file stored at `data/scms.db`. It contains **9 tables** that together support authentication, attendance tracking, academic performance, resource management, safety alerts, and analytics.

SQLite **foreign-key enforcement must be enabled** at connection time:

```python
connection.execute("PRAGMA foreign_keys = ON;")
```

All date values are stored as plain text in ISO format:

| Value type | Format               | Example               |
|------------|----------------------|-----------------------|
| Date only  | `YYYY-MM-DD`         | `2024-03-15`          |
| Datetime   | `YYYY-MM-DD HH:MM:SS`| `2024-03-15 09:30:00` |

---

## Table List

| # | Table       | Purpose                                          |
|---|-------------|--------------------------------------------------|
| 1 | `users`     | Authentication and role information for all users |
| 2 | `classes`   | Classroom sections                               |
| 3 | `subjects`  | Subjects belonging to a class                    |
| 4 | `students`  | Student-specific profile data                    |
| 5 | `attendance`| One attendance record per student, subject, date |
| 6 | `marks`     | Student test/exam results                        |
| 7 | `resources` | Classroom equipment inventory                    |
| 8 | `bookings`  | Resource booking and return history              |
| 9 | `alerts`    | Safety and security incidents                    |

---

## Table Definitions

---

### 1. `users`

Central authentication and role table. Every person who can log in to SCMS — admin, teacher, or student — has exactly one row here.

| Column          | Type    | Constraints              | Purpose                                      |
|-----------------|---------|--------------------------|----------------------------------------------|
| `id`            | INTEGER | PK, AUTOINCREMENT        | Surrogate primary key                        |
| `name`          | TEXT    | NOT NULL                 | Full display name                            |
| `role`          | TEXT    | NOT NULL, CHECK          | One of: `admin`, `teacher`, `student`        |
| `username`      | TEXT    | NOT NULL, UNIQUE         | Login identifier                             |
| `password_hash` | TEXT    | NOT NULL                 | PBKDF2-HMAC-SHA256 derived key (hex string)  |
| `password_salt` | TEXT    | NOT NULL                 | Random salt used during hashing (hex string) |

**Password handling:** Passwords are hashed with `hashlib.pbkdf2_hmac('sha256', ...)` using a randomly generated per-user salt. Neither the plain-text password nor a reversible encoding is stored.

**Referenced by:** `classes.teacher_id`, `students.user_id`, `bookings.booked_by`, `alerts.created_by`, `alerts.resolved_by`

---

### 2. `classes`

Represents a classroom section (e.g. `"CS-A 2nd Year"`). Each class has one assigned class teacher.

| Column       | Type    | Constraints              | Purpose                                      |
|--------------|---------|--------------------------|----------------------------------------------|
| `id`         | INTEGER | PK, AUTOINCREMENT        | Surrogate primary key                        |
| `class_name` | TEXT    | NOT NULL, UNIQUE         | Human-readable section name                  |
| `teacher_id` | INTEGER | NOT NULL, FK → users(id) | The class teacher (must be role = `teacher`) |

**Referenced by:** `subjects.class_id`, `students.class_id`

---

### 3. `subjects`

Canonical list of subjects offered in each class. Subjects are referenced by ID in `attendance` and `marks` to avoid free-text inconsistencies.

| Column     | Type    | Constraints               | Purpose                                |
|------------|---------|---------------------------|----------------------------------------|
| `id`       | INTEGER | PK, AUTOINCREMENT         | Surrogate primary key                  |
| `name`     | TEXT    | NOT NULL                  | Subject name (e.g. `"Mathematics"`)    |
| `class_id` | INTEGER | NOT NULL, FK → classes(id)| The class this subject belongs to      |

**Constraint:** `UNIQUE (name, class_id)` — the same subject name cannot appear twice within the same class.

**Referenced by:** `attendance.subject_id`, `marks.subject_id`

---

### 4. `students`

Student-specific profile data extending the `users` table. Every student account in `users` has exactly one corresponding row here.

| Column        | Type    | Constraints               | Purpose                          |
|---------------|---------|---------------------------|----------------------------------|
| `id`          | INTEGER | PK, AUTOINCREMENT         | Surrogate primary key            |
| `user_id`     | INTEGER | NOT NULL, UNIQUE, FK → users(id) | Links to the login account  |
| `roll_number` | TEXT    | NOT NULL, UNIQUE          | Institutional roll number        |
| `class_id`    | INTEGER | NOT NULL, FK → classes(id)| The class this student belongs to|

**Referenced by:** `attendance.student_id`, `marks.student_id`

---

### 5. `attendance`

Stores one attendance record per student per subject per date. A student is either `Present` or `Absent` for each subject on each school day.

| Column       | Type    | Constraints                | Purpose                             |
|--------------|---------|----------------------------|-------------------------------------|
| `id`         | INTEGER | PK, AUTOINCREMENT          | Surrogate primary key               |
| `student_id` | INTEGER | NOT NULL, FK → students(id)| The student being marked            |
| `subject_id` | INTEGER | NOT NULL, FK → subjects(id)| The subject being attended          |
| `date`       | TEXT    | NOT NULL                   | Date of class (`YYYY-MM-DD`)        |
| `status`     | TEXT    | NOT NULL, CHECK            | One of: `Present`, `Absent`         |

**Constraint:** `UNIQUE (student_id, subject_id, date)` — prevents a student from being marked twice for the same subject on the same day.

> **Note:** A student's class is derived through `students.class_id`. `class_id` is intentionally **not** stored here to avoid redundancy.

---

### 6. `marks`

Stores individual test or exam scores. Multiple test entries per subject per student are supported, enabling averages to be computed.

| Column           | Type    | Constraints                | Purpose                               |
|------------------|---------|----------------------------|---------------------------------------|
| `id`             | INTEGER | PK, AUTOINCREMENT          | Surrogate primary key                 |
| `student_id`     | INTEGER | NOT NULL, FK → students(id)| The student being assessed            |
| `subject_id`     | INTEGER | NOT NULL, FK → subjects(id)| The subject being tested              |
| `test_name`      | TEXT    | NOT NULL                   | Name of the test (e.g. `"Unit Test 1"`) |
| `marks_obtained` | REAL    | NOT NULL, CHECK            | Score the student received (≥ 0)      |
| `max_marks`      | REAL    | NOT NULL, CHECK            | Maximum possible score (> 0)          |
| `date`           | TEXT    | NOT NULL                   | Date of the test (`YYYY-MM-DD`)       |

**Validation constraints:**
- `marks_obtained >= 0`
- `max_marks > 0`
- `marks_obtained <= max_marks`

---

### 7. `resources`

Classroom equipment inventory. Each resource has a current status that changes when it is booked, returned, or sent for maintenance.

| Column               | Type    | Constraints       | Purpose                                                    |
|----------------------|---------|-------------------|------------------------------------------------------------|
| `id`                 | INTEGER | PK, AUTOINCREMENT | Surrogate primary key                                      |
| `resource_code`      | TEXT    | NOT NULL, UNIQUE  | Short identifier (e.g. `"R01"`)                            |
| `name`               | TEXT    | NOT NULL          | Human-readable name (e.g. `"Projector"`)                  |
| `status`             | TEXT    | NOT NULL, CHECK   | One of: `Available`, `In Use`, `Maintenance`               |
| `maintenance_notes`  | TEXT    | —                 | Optional notes about maintenance (NULL if not applicable)  |

**Default status:** `Available`

**Referenced by:** `bookings.resource_id`

---

### 8. `bookings`

Maintains the history of every resource booking and return. An open booking (resource not yet returned) is identified by `returned_at IS NULL`.

| Column        | Type    | Constraints                | Purpose                                           |
|---------------|---------|----------------------------|---------------------------------------------------|
| `id`          | INTEGER | PK, AUTOINCREMENT          | Surrogate primary key                             |
| `resource_id` | INTEGER | NOT NULL, FK → resources(id)| The resource being booked                        |
| `booked_by`   | INTEGER | NOT NULL, FK → users(id)   | The teacher or admin who booked the resource      |
| `booked_at`   | TEXT    | NOT NULL                   | Booking datetime (`YYYY-MM-DD HH:MM:SS`)         |
| `returned_at` | TEXT    | —                          | Return datetime — NULL means not yet returned     |

**Active booking rule:** Before inserting a new booking, the application must verify that no existing row exists for `resource_id` where `returned_at IS NULL`. This check is enforced in application logic (`resources.py`), not via a database trigger, to keep the schema simple.

---

### 9. `alerts`

Records safety and security incidents. Alerts are created by teachers or admins and resolved exclusively by admins.

| Column        | Type    | Constraints              | Purpose                                             |
|---------------|---------|--------------------------|-----------------------------------------------------|
| `id`          | INTEGER | PK, AUTOINCREMENT        | Surrogate primary key                               |
| `alert_type`  | TEXT    | NOT NULL, CHECK          | One of: `Fire`, `Unauthorized Access`, `Medical`, `Other` |
| `location`    | TEXT    | NOT NULL                 | Where the incident occurred (e.g. `"Room 204"`)    |
| `description` | TEXT    | —                        | Optional free-text detail                           |
| `status`      | TEXT    | NOT NULL, CHECK          | One of: `Active`, `Resolved`                        |
| `created_by`  | INTEGER | NOT NULL, FK → users(id) | User who raised the alert                           |
| `created_at`  | TEXT    | NOT NULL                 | Alert creation datetime (`YYYY-MM-DD HH:MM:SS`)    |
| `resolved_by` | INTEGER | FK → users(id)           | Admin who resolved the alert — NULL until resolved  |
| `resolved_at` | TEXT    | —                        | Resolution datetime — NULL until resolved           |

**Default status:** `Active`

---

## Entity-Relationship Summary

```
users ──────────────────────────────────────────────┐
  │  (role=teacher)                                  │
  │ teacher_id                                       │
  ▼                                                  │
classes ──────────────────────────────────┐          │
  │ class_id                              │          │
  ▼                                       │          │
subjects                                  │          │
  │ subject_id                            │ class_id │ user_id
  │                                       ▼          ▼
  │                                     students ────┘
  │                                       │ student_id
  │                              ┌────────┴────────┐
  │                              ▼                 ▼
  └──────────────────────► attendance            marks
                                                  
users ──── booked_by ────► bookings ◄──── resource_id ──── resources
users ──── created_by ───► alerts ◄──── resolved_by ────── users
```

---

## Business Rules and Thresholds

### Attendance Rules

| Metric                | Condition   | Label / Action           |
|-----------------------|-------------|--------------------------|
| Subject attendance %  | < 75%       | `LOW` — flag the student |
| Subject attendance %  | ≥ 75%       | `GOOD`                   |
| Overall attendance %  | < 75%       | `LOW` — flag the student |
| Overall attendance %  | ≥ 75%       | `GOOD`                   |

**Attendance % formula (per subject):**

```
attendance_pct = (count of Present records) / (total records) × 100
```

---

### Marks Validation Rules

- `marks_obtained` must be ≥ 0
- `max_marks` must be > 0
- `marks_obtained` must be ≤ `max_marks`

These constraints are enforced both in the database (CHECK constraints) and in application input validation.

**Subject average formula:**

```
subject_avg_pct = SUM(marks_obtained) / SUM(max_marks) × 100
```

(Summing across all tests for a student in a subject gives a weighted average.)

---

### Learning-Gap Detection Thresholds

These thresholds are applied by `learning_gap.py` at runtime. They are deterministic rules — no machine learning is involved.

| Metric                | Condition   | Label               |
|-----------------------|-------------|---------------------|
| Subject average %     | < 50%       | `NEEDS IMPROVEMENT` |
| Subject average %     | ≥ 50%       | `GOOD`              |
| Subject attendance %  | < 75%       | Attendance concern  |

A student is flagged as **at risk** if any subject has average marks below 50% **or** attendance below 75%.

---

### Resource Status Rules

| Status        | Meaning                                               |
|---------------|-------------------------------------------------------|
| `Available`   | Resource is in the room and can be booked             |
| `In Use`      | Resource has an active booking (returned_at IS NULL)  |
| `Maintenance` | Resource is under repair — cannot be booked           |

**Allowed transitions:**

```
Available  →  In Use       (booking created)
In Use     →  Available    (booking returned)
Available  →  Maintenance  (admin marks for maintenance)
Maintenance→  Available    (admin clears maintenance)
```

---

### Safety Alert Status Rules

| Status     | Meaning                                           |
|------------|---------------------------------------------------|
| `Active`   | Incident has been reported and not yet resolved   |
| `Resolved` | Admin has marked the incident as resolved         |

Only an **admin** can transition an alert from `Active` to `Resolved`. Resolution always records `resolved_by` and `resolved_at`.

---

## Complete SQL Schema

The following SQL is used by `database.py` to initialise the database. Tables must be created in this order to satisfy foreign-key dependencies.

```sql
-- Enable foreign key enforcement (must also be set at connection time in Python)
PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────
-- 1. users
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    password_salt TEXT    NOT NULL
);

-- ─────────────────────────────────────────────
-- 2. classes
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS classes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    class_name   TEXT    NOT NULL UNIQUE,
    teacher_id   INTEGER NOT NULL REFERENCES users(id)
);

-- ─────────────────────────────────────────────
-- 3. subjects
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subjects (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL,
    class_id INTEGER NOT NULL REFERENCES classes(id),
    UNIQUE (name, class_id)
);

-- ─────────────────────────────────────────────
-- 4. students
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE REFERENCES users(id),
    roll_number TEXT    NOT NULL UNIQUE,
    class_id    INTEGER NOT NULL REFERENCES classes(id)
);

-- ─────────────────────────────────────────────
-- 5. attendance
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    date       TEXT    NOT NULL,
    status     TEXT    NOT NULL CHECK(status IN ('Present', 'Absent')),
    UNIQUE (student_id, subject_id, date)
);

-- ─────────────────────────────────────────────
-- 6. marks
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS marks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id),
    subject_id      INTEGER NOT NULL REFERENCES subjects(id),
    test_name       TEXT    NOT NULL,
    marks_obtained  REAL    NOT NULL CHECK(marks_obtained >= 0),
    max_marks       REAL    NOT NULL CHECK(max_marks > 0),
    date            TEXT    NOT NULL,
    CHECK (marks_obtained <= max_marks)
);

-- ─────────────────────────────────────────────
-- 7. resources
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resources (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_code      TEXT    NOT NULL UNIQUE,
    name               TEXT    NOT NULL,
    status             TEXT    NOT NULL DEFAULT 'Available'
                               CHECK(status IN ('Available', 'In Use', 'Maintenance')),
    maintenance_notes  TEXT
);

-- ─────────────────────────────────────────────
-- 8. bookings
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bookings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    booked_by   INTEGER NOT NULL REFERENCES users(id),
    booked_at   TEXT    NOT NULL,
    returned_at TEXT
);

-- ─────────────────────────────────────────────
-- 9. alerts
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type   TEXT    NOT NULL CHECK(alert_type IN ('Fire', 'Unauthorized Access', 'Medical', 'Other')),
    location     TEXT    NOT NULL,
    description  TEXT,
    status       TEXT    NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Resolved')),
    created_by   INTEGER NOT NULL REFERENCES users(id),
    created_at   TEXT    NOT NULL,
    resolved_by  INTEGER REFERENCES users(id),
    resolved_at  TEXT
);
```

---

## Seed Data Plan (for `seed.py`)

The seed script should create enough data for a meaningful demonstration without being unnecessarily large. Target volumes:

| Entity              | Target count                                  |
|---------------------|-----------------------------------------------|
| Admin accounts      | 1                                             |
| Teacher accounts    | 2                                             |
| Classes             | 2                                             |
| Subjects per class  | 3                                             |
| Students total      | 8–10 (split across the 2 classes)             |
| Attendance days     | 15–20 school days per subject per student     |
| Tests per student   | 2–3 per subject                               |
| Resources           | 4–5                                           |
| Sample bookings     | 4–6 (mix of returned and still active)        |
| Sample alerts       | 3–4 (mix of Active and Resolved)              |

---

*Last updated: 08-Sep-2026 · SCMS prototype*