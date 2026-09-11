# Smart Classroom Management System (SCMS)

A simple, terminal-based college prototype for managing classroom attendance, student performance, equipment bookings, safety alerts, and institutional analytics — built with Python and SQLite.

---

## Overview

Most classrooms rely on paper attendance registers, printed mark sheets, and manual logbooks for shared equipment. **SCMS** is a lightweight command-line project that centralizes these day-to-day operations into one local, role-based application.

Students, teachers, and administrators each get a focused dashboard tailored to their responsibilities, backed by a local SQLite database.

> **Note:** This project is an educational terminal prototype. It runs entirely on the **Python standard library** with zero external packages. It does not require any cloud servers, internet connection, or web frameworks.

---

## Role Permissions & Features

Every user belongs to one of three roles: **Student**, **Teacher**, or **Admin**.

| Feature / Capability | Student | Teacher | Admin |
|---|:---:|:---:|:---:|
| **View Own Attendance** (overall & subject-wise) | ✅ | — | — |
| **View Own Marks & Performance** (test scores & averages) | ✅ | — | — |
| **View Learning Gaps & Recommendations** | ✅ | — | — |
| **Rule-Based Learning Assistant** (offline Q&A) | ✅ | — | — |
| **Book & Return Resources** | ✅ | ✅ | ✅ |
| **View Personal Booking History** | ✅ | ✅ | ✅ |
| **Mark Resource for Maintenance & Release** | — | ✅ | ✅ |
| **View Complete Resource Booking History** (all users) | — | ✅ | ✅ |
| **Report Safety Alert** (simulated incident) | ✅ | ✅ | ✅ |
| **Resolve Safety Alert** | — | ✅ | ✅ |
| **Institutional Analytics & Reports** (6 aggregate views) | — | ✅ | ✅ |
| **Manage Users** (view & create accounts) | — | — | ✅ |
| **Manage Classes & Subjects** (view & create) | — | — | ✅ |

*(Note: Manual teacher attendance marking and mark entry are designated as coming soon on the future roadmap; attendance and marks are currently populated via the database seeder.)*

---

## Key Modules & Logic

### 1. Attendance Tracking
Students can view their subject-wise and overall attendance percentage, along with total present/absent class counts.
- **Threshold Rule:** Attendance **< 75%** is flagged as `LOW`. Attendance **≥ 75%** is marked `GOOD`.

### 2. Academic Performance & Marks
Students can view individual test scores (Unit Test 1, Midterm, Final) and subject averages.
- **Threshold Rule:** Performance **< 50%** is flagged as `NEEDS IMPROVEMENT`. Performance **≥ 50%** is marked `GOOD`.

### 3. Learning Gap Detection
A deterministic, rule-based algorithm (no machine learning) that evaluates both attendance and performance data to highlight subjects where the student needs extra support:
- `HIGH` Priority: Both attendance < 75% **and** marks < 50% (attendance & conceptual gap).
- `MEDIUM` Priority: Either attendance < 75% **or** marks < 50%.
- `NONE`: Attendance ≥ 75% **and** marks ≥ 50% (on track).

### 4. Rule-Based Learning Assistant
An offline helper for students that answers 5 predefined queries directly from their local data:
1. *My attendance* — summary of all enrolled subjects and statuses.
2. *My marks* — subject-wise test performance.
3. *My learning gaps* — detected priority gaps with tailored study suggestions.
4. *What should I improve?* — actionable study recommendations for weak areas.
5. *Ask about a subject* — lookup attendance, score, and gap status for a specific subject (e.g., `Mathematics`). Safely rejects invalid subjects.

### 5. Resource Management
Tracks shared classroom equipment (projectors, smart boards, computers, speakers, HDMI kits).
- **Statuses:** `Available`, `In Use`, `Maintenance`.
- **Workflow:**
  - Any user can book an `Available` resource (status becomes `In Use`).
  - The booking user returns the resource (status reverts to `Available`).
  - Teachers and Admins can place an item into `Maintenance` with notes, and release it when repaired.
  - Students see their own booking history; Teachers and Admins see complete booking logs.

### 6. Safety & Security Alerts
A software simulation representing campus safety incident reporting:
- **Incident Types:** `Fire`, `Unauthorized Access`, `Medical`, `Other`.
- **Workflow:**
  - Students, teachers, and admins can report active incidents with location and description.
  - Teachers and admins can review active alerts and mark them as `Resolved`.
  - Full incident history is maintained.

### 7. Institutional Analytics & Reports
Provides 6 aggregate statistics for teachers and administrators:
1. **Dashboard Summary:** Total counts of students, classes, subjects, resources, and alerts.
2. **Attendance Analytics:** Institution-wide attendance rate and per-subject averages.
3. **Performance Analytics:** Institution-wide score average and pass/fail distributions.
4. **Student Performance Summary:** Student-by-student matrix showing attendance and marks status.
5. **Resource Usage:** Most frequently booked resources and current inventory status.
6. **Safety Alert Statistics:** Breakdown of incidents by type and resolution status.

### 8. Admin Management
Administrators can:
- View all system users (passwords and password hashes are never displayed).
- Add new student, teacher, or admin accounts with secure PBKDF2-HMAC-SHA256 password hashing.
- View and create classes and subjects.

---

## Screenshots

### 1. Login
<!-- Add screenshot here -->

### 2. Student Dashboard
<!-- Add screenshot here -->

### 3. Attendance
<!-- Add screenshot here -->

### 4. Learning Gaps / Learning Assistant
<!-- Add screenshot here -->

### 5. Resource Management
<!-- Add screenshot here -->

### 6. Safety & Security Alerts
<!-- Add screenshot here -->

### 7. Teacher Analytics
<!-- Add screenshot here -->

### 8. Admin Dashboard
<!-- Add screenshot here -->

---

## Tech Stack & Architecture

- **Language:** Python 3.9+
- **Database:** SQLite 3 (`data/scms.db`)
- **Interface:** Command-Line Interface (CLI / Terminal)
- **External Dependencies:** **None** (uses standard library modules: `sqlite3`, `hashlib`, `secrets`, `hmac`, `getpass`, `sys`, `os`).

```
                    Terminal / CLI (main.py)
                                │
                    Authentication (auth.py)
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
      Student Menu         Teacher Menu         Admin Menu
      (student.py)         (teacher.py)         (admin.py)
            │                   │                   │
            └───────────┬───────┴───────────┬───────┘
                        ▼                   ▼
                 Domain Modules       Domain Modules
              (attendance, marks,   (resources, alerts,
                learning_gap, etc.)     analytics)
                        │                   │
                        └─────────┬─────────┘
                                  ▼
                        Database Layer (database.py)
                                  ▼
                         SQLite (data/scms.db)
```

---

## Project Structure

```
SmartClassroom/
├── main.py                     # Application entry point, login loop & role routing
├── database.py                 # SQLite connection handling & 9-table schema init
├── seed.py                     # Populates demo database with realistic test data
├── requirements.txt            # Project dependencies note (standard library only)
├── .gitignore                  # Ignores data/*.db, __pycache__/, *.pyc, venv/
├── docs/
│   └── SCHEMA.md               # Detailed database schema reference & constraints
└── modules/
    ├── auth.py                 # PBKDF2 password hashing & authentication
    ├── student.py              # Student dashboard & menus
    ├── teacher.py              # Teacher dashboard & menus
    ├── admin.py                # Admin dashboard & management menus
    ├── attendance.py           # Attendance percentage & threshold calculations
    ├── marks.py                # Test marks aggregation & performance calculations
    ├── learning_gap.py         # Rule-based gap detection logic
    ├── learning_assistant.py   # Offline rule-based student Q&A assistant
    ├── resources.py            # Resource booking, return & maintenance transactions
    ├── alerts.py               # Safety incident reporting & resolution lifecycle
    └── analytics.py            # Aggregate institutional analytics & statistics
```

---

## Getting Started

### 1. Prerequisites
Python 3.9 or higher installed.

### 2. Setup & Execution
Clone the repository and open the project directory:

```bash
cd SmartClassroom
```

Initialize and populate the local SQLite demo database:

```bash
python3 seed.py
```

Run the application:

```bash
python3 main.py
```

---

## Demo Login Credentials

The `seed.py` script creates ready-to-use demo accounts for testing all three roles:

| Role | Username | Password | Purpose |
|---|---|---|---|
| **Admin** | `admin` | `Admin@123` | Full administrative, user & resource control |
| **Teacher** | `priya_t` | `Teacher@1` | Resources, safety alerts, analytics |
| **Teacher** | `rahul_t` | `Teacher@2` | Second teacher account |
| **Student** | `ananya_s` | `Pass@1234` | High attendance (88.9%) & good marks (78.3%) |
| **Student** | `rohit_s` | `Pass@1234` | Low attendance (50.0%) & borderline marks (50.7%) |
| **Student** | `pooja_s` | `Pass@1234` | Low attendance (50.0%) & borderline marks (51.3%) |

*(All other demo student accounts use password: `Pass@1234`)*

---

## Deliberate Scope Limitations & Future Roadmap

This prototype is intentionally designed as an offline software simulation for college demonstration:
- **No Physical Hardware:** Alerts and resource tracking are software simulations; they are not wired to physical IoT sensors, RFID scanners, or fire panels.
- **No Cloud / External APIs:** All data is kept in a local SQLite file. The learning assistant uses deterministic data queries without third-party LLM or machine learning APIs.
- **No Biometrics:** Attendance is record-based rather than using facial recognition or fingerprint scanning.

### Planned Future Roadmap
1. **Academic Entry:** Interactive forms for teachers to mark daily attendance and enter test marks directly via CLI/UI.
2. **Automated Check-in:** Camera-based facial recognition or QR code scanning for classroom entry.
3. **Hardware Integration:** IoT smart tags for resource tracking and physical fire panel / door relay triggers for safety alerts.
4. **AI Assistant:** Optional integration with local or cloud LLMs for free-form conversational student tutoring.
5. **Web & Mobile Frontends:** REST API backend and responsive web portal.