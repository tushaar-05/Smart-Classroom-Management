<div align="center">

# SCMS
### Smart Classroom Management System

*A terminal-based platform for attendance, performance, resources, and safety — built for the classroom, not the cloud.*

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-07405E?logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Prototype-F5A623)
![License](https://img.shields.io/badge/License-Educational-2E8B57)

[Overview](#overview) • [Features](#features) • [Modules](#modules) • [Setup](#getting-started) • [Roadmap](#roadmap)

</div>

---

## Overview

Most classrooms still run on paper — attendance registers, mark sheets, verbal handoffs for shared equipment, and ad-hoc incident reports. It works, but it's slow, error-prone, and impossible to analyze later.

**SCMS replaces that with one role-based system.** Students, teachers, and admins each get a scoped view of exactly what they need, all backed by a single local database.

> **Why a terminal app, not a website?** No servers, no hosting, no frontend to maintain — just the logic, running anywhere Python runs. The goal here is to prove the workflow, not ship a production stack.

<table>
<tr>
<td><b>Year</b></td><td>2024</td>
<td><b>Domain</b></td><td>Smart Automation</td>
</tr>
<tr>
<td><b>Organisation</b></td><td>Govt. of NCT of Delhi</td>
<td><b>Department</b></td><td>Education</td>
</tr>
</table>

---

## Features

Every action in SCMS is gated by role.

| Capability | Student | Teacher | Admin |
|---|:---:|:---:|:---:|
| View profile & attendance | ✅ | ✅ | ✅ |
| Mark attendance | — | ✅ | ✅ |
| View marks | ✅ | ✅ | ✅ |
| Enter marks | — | ✅ | ✅ |
| Learning gap analysis | ✅ | ✅ | ✅ |
| Learning assistant | ✅ | — | — |
| Book / return resources | — | ✅ | ✅ |
| Create safety alert | — | ✅ | ✅ |
| Resolve safety alert | — | — | ✅ |
| Manage students / teachers / classes | — | — | ✅ |

---

## Modules

<details>
<summary><b>Attendance</b> — recording, reporting, and low-attendance flags</summary><br>

Teachers mark attendance per student, per class, per date. SCMS rolls this up into subject-wise and overall percentages, flagging anything under **75%** as `LOW`.

```
ATTENDANCE REPORT
----------------------------------------
Subject          Present   Total    %
----------------------------------------
Mathematics         18       20     90%
Programming         16       20     80%
Physics             17       20     85%

Overall Attendance: 85%   Status: GOOD
```
</details>

<details>
<summary><b>Academic Performance</b> — marks entry and subject averages</summary><br>

Teachers enter marks by subject and test. SCMS computes averages and flags any subject under **50%** as `NEEDS IMPROVEMENT`. This feeds directly into learning gap detection.
</details>

<details>
<summary><b>Learning Gap Detection</b> — rule-based, not ML</summary><br>

Deterministic rules over marks and attendance data — no trained model. Transparent, testable, and demo-safe.

```
LEARNING GAPS
----------------------------------------
Programming : Good
Mathematics  : Needs Improvement
Physics      : Needs Improvement

Suggested Focus: Matrix Operations, Linear Equations, Mechanics
```
</details>

<details>
<summary><b>Learning Assistant</b> — offline Q&A for students</summary><br>

Answers a fixed set of queries using the student's own stored data. No external API calls:

```
> Which subject should I focus on?
> What are my weak subjects?
> Why is my performance low?
> Give me study suggestions
```

A live LLM-backed version is on the [roadmap](#roadmap) once the core data pipeline is proven out.
</details>

<details>
<summary><b>Resource Management</b> — projectors, boards, and everything in between</summary><br>

Every resource is `Available`, `In Use`, or `Maintenance`. Teachers and admins book, return, and flag equipment.

```
CLASSROOM RESOURCES
----------------------------------------
ID     Resource          Status
----------------------------------------
R01    Projector         Available
R02    Smart Board       In Use
R03    Computer          Available
R04    Microphone        Maintenance
```
</details>

<details>
<summary><b>Safety Alerts</b> — incident logging and resolution</summary><br>

Fire, unauthorized access, medical, or other incidents — logged with location and description, resolved by admins. Simulates the workflow only; no hardware integration.

```
ACTIVE ALERTS
----------------------------------------
ID     Type              Location
----------------------------------------
A001   FIRE              Room 204
A002   MEDICAL           Room 101
```
</details>

<details>
<summary><b>Analytics</b> — the classroom, at a glance</summary><br>

```
CLASSROOM ANALYTICS
========================================
Total Students          : 45
Average Attendance      : 84.6%
Average Marks           : 76.3%
Low Attendance Students : 6
Students Needing Help   : 8
Most Used Resource      : Projector
```
</details>

---

## Architecture

```
              Terminal / CLI
                    │
             Application Logic
                    │
   ┌──────────┬──────────┬──────────┐
   │Attendance│Resources │Analytics │  Alerts
   └──────────┴──────────┴──────────┘
                    │
             SQLite Database
```

Runs entirely locally — no server, no cloud dependency, single-file database. Full schema and threshold rules live in [`docs/SCHEMA.md`](docs/SCHEMA.md).

---

## Tech Stack

| | |
|---|---|
| **Language** | Python 3.9+ |
| **Database** | SQLite |
| **Interface** | CLI |
| **VCS** | Git |

---

## Project Structure

```
SCMS/
├── main.py                     # Entry point, login routing, role-based menus
├── database.py                 # Connection handling, schema init
├── seed.py                     # Sample data for demos
├── requirements.txt
├── modules/
│   ├── auth.py                 # Login, password hashing
│   ├── student.py               # Student menu & actions
│   ├── teacher.py                # Teacher menu & actions
│   ├── admin.py                   # Admin menu & actions
│   ├── attendance.py               # Marking & reporting
│   ├── marks.py                     # Entry & performance calc
│   ├── learning_gap.py               # Rule-based gap detection
│   ├── learning_assistant.py          # Rule-based Q&A
│   ├── resources.py                    # Booking / return / maintenance
│   ├── alerts.py                        # Safety alert lifecycle
│   └── analytics.py                      # Aggregate reporting
├── docs/
│   └── SCHEMA.md                # Full DB schema + threshold rules
└── data/
    └── scms.db
```

---

## Getting Started

```bash
git clone https://github.com/tushaar-05/Smart-Classroom-Management.git
cd Smart-Classroom-Management

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
python3 seed.py                 # populates sample data
python3 main.py
```

Requires **Python 3.9+**.

---

## Workflows

| Flow | Steps |
|---|---|
| **Academic** | Login → select class → mark attendance → enter marks → performance calculated → gaps flagged → report generated |
| **Resource booking** | View resources → book → use → return |
| **Safety incident** | Incident occurs → alert created → admin reviews → resolved |

---

## Limitations

By design, this prototype does **not** include: facial recognition, physical hardware integration (CCTV, fire panels), real-time push notifications, cloud infrastructure, machine learning, or external AI services. Each is a deliberate next step — see below.

## Roadmap

| Area | Planned |
|---|---|
| Attendance | Facial recognition, QR check-in, mobile app |
| Resources | IoT-based tracking, automated status |
| Safety | CCTV/fire-panel integration, SMS/email alerts |
| Learning | LLM-backed assistant, predictive gap detection |
| Analytics | ML forecasting, interactive dashboards |
| Infrastructure | Web/mobile clients, cloud database |

---

<div align="center">

**SCMS** · built as an educational prototype for the *Smart Classroom Management Software* problem statement
Govt. of NCT of Delhi · Education Department · 2024

</div>