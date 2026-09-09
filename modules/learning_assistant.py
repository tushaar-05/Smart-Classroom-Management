"""
modules/learning_assistant.py — SCMS Rule-Based Learning Assistant
===================================================================
Provides fixed-query, rule-based responses to student questions about
their attendance, performance, and learning gaps.

This is a RULE-BASED assistant, NOT:
  - An AI chatbot
  - A generative AI system
  - A machine-learning model
  - An NLP system
  - An external API integration

Every response is deterministic: the same student data always produces
the same response. No randomness, no network calls, no AI inference.

Architecture:
  student.py (menu / I/O)
      ↓
  learning_assistant.py (response generation)
      ↓
  learning_gap.get_learning_gaps()   ← reused from Step 10
  attendance.get_subject_attendance()
  marks.get_subject_performance()
      ↓
  database.py → SQLite

Design rules enforced in this module:
  - Contains no user-input calls
  - Contains no terminal output calls
  - No external API calls
  - No ML/NLP libraries
  - No duplicated threshold constants (imported from source modules)
  - No duplicated learning-gap rules (reused from learning_gap.py)
  - All SQL, if any, uses parameterized queries

Subject-name matching for option 5 (ask about a subject):
  The student types a subject name (e.g. "Mathematics"). We look it up
  only among the subjects that belong to THIS student's gap data, which
  is keyed by subject_id (not by name). This prevents matching the wrong
  class's "Mathematics" subject.

Schema reference: docs/SCHEMA.md
"""

from modules.learning_gap import get_learning_gaps


# ---------------------------------------------------------------------------
# 1. Attendance summary
# ---------------------------------------------------------------------------

def get_attendance_summary(student_id: int) -> list[dict]:
    """
    Return a short per-subject attendance summary for the assistant.

    Reuses get_learning_gaps() which already contains per-subject
    attendance data alongside other information. This avoids duplicating
    the attendance query.

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        List of dicts sorted by subject name. Each dict:
            subject_name          str
            attendance_percentage float | None
            attendance_status     str   ("LOW" | "GOOD" | "NO DATA")
    """
    gaps = get_learning_gaps(student_id)
    # Sort alphabetically for consistent display.
    sorted_gaps = sorted(gaps, key=lambda g: g["subject_name"])
    return [
        {
            "subject_name"         : g["subject_name"],
            "attendance_percentage": g["attendance_percentage"],
            "attendance_status"    : g["attendance_status"],
        }
        for g in sorted_gaps
    ]


# ---------------------------------------------------------------------------
# 2. Marks / performance summary
# ---------------------------------------------------------------------------

def get_performance_summary(student_id: int) -> list[dict]:
    """
    Return a short per-subject performance summary for the assistant.

    Reuses get_learning_gaps() to avoid duplicating marks queries.

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        List of dicts sorted by subject name. Each dict:
            subject_name           str
            performance_percentage float | None
            performance_status     str   ("NEEDS IMPROVEMENT" | "GOOD" | "NO DATA")
    """
    gaps = get_learning_gaps(student_id)
    sorted_gaps = sorted(gaps, key=lambda g: g["subject_name"])
    return [
        {
            "subject_name"          : g["subject_name"],
            "performance_percentage": g["performance_percentage"],
            "performance_status"    : g["performance_status"],
        }
        for g in sorted_gaps
    ]


# ---------------------------------------------------------------------------
# 3. Learning gaps summary
# ---------------------------------------------------------------------------

def get_gaps_summary(student_id: int) -> list[dict]:
    """
    Return the learning gap results for the assistant display.

    Directly delegates to get_learning_gaps() — no new logic here.
    The assistant option 3 shows the same information as the standalone
    Learning Gap screen, in a slightly shorter format.

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        Same list returned by get_learning_gaps(). Empty list if no data.
    """
    return get_learning_gaps(student_id)


# ---------------------------------------------------------------------------
# 4. What should I improve? (improvement advice)
# ---------------------------------------------------------------------------

def get_improvement_advice(student_id: int) -> dict:
    """
    Generate a prioritised improvement recommendation.

    Logic (uses existing gap data — no new rules):
        HIGH gaps exist  → these subjects need the most attention.
        Only MEDIUM gaps → these subjects need attention.
        No gaps at all   → give a positive acknowledgement message.

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        Dict with keys:
            has_high    bool
            has_medium  bool
            high_gaps   list[dict]   gaps with priority=="HIGH"
            medium_gaps list[dict]   gaps with priority=="MEDIUM"
            message     str          top-level text to display
    """
    gaps = get_learning_gaps(student_id)

    high_gaps   = [g for g in gaps if g["priority"] == "HIGH"]
    medium_gaps = [g for g in gaps if g["priority"] == "MEDIUM"]

    has_high   = len(high_gaps)   > 0
    has_medium = len(medium_gaps) > 0

    if has_high:
        subjects = ", ".join(g["subject_name"] for g in high_gaps)
        message = (
            f"These subjects need your immediate attention: {subjects}.\n"
            f"Both attendance and performance are below the required thresholds."
        )
    elif has_medium:
        subjects = ", ".join(g["subject_name"] for g in medium_gaps)
        message = (
            f"These subjects need some improvement: {subjects}.\n"
            f"Review the specific recommendations below."
        )
    else:
        message = (
            "Your current attendance and performance look good.\n"
            "Keep maintaining your current study habits."
        )

    return {
        "has_high"   : has_high,
        "has_medium" : has_medium,
        "high_gaps"  : high_gaps,
        "medium_gaps": medium_gaps,
        "message"    : message,
    }


# ---------------------------------------------------------------------------
# 5. Ask about a specific subject
# ---------------------------------------------------------------------------

def get_subject_info(student_id: int, query: str) -> dict | None:
    """
    Look up gap information for a subject by the student's typed name.

    Subject matching strategy:
        1. Get gap data for this student (keyed by subject_id).
        2. Search among ONLY this student's subjects (not all subjects
           in the database) to prevent mixing data from another class's
           subject with the same name.
        3. Match case-insensitively against the typed query string.
        4. Return the first match, or None if no match.

    Why this is safe against class mixing:
        get_learning_gaps() already returns only subjects for this
        student_id. Each subject in the result has a unique subject_id.
        Even if two classes both have "Mathematics", a student can only
        see the Mathematics that belongs to their own class's subject_id.

    Parameters:
        student_id — students.id (NOT users.id)
        query      — the subject name string typed by the student

    Returns:
        The matching gap dict (from get_learning_gaps), or None.
    """
    gaps = get_learning_gaps(student_id)
    query_lower = query.strip().lower()

    for g in gaps:
        if g["subject_name"].lower() == query_lower:
            return g

    # Also try partial / starts-with matching for usability
    # e.g. "math" → "Mathematics"
    for g in gaps:
        if g["subject_name"].lower().startswith(query_lower):
            return g

    return None


# ---------------------------------------------------------------------------
# 6. List enrolled subject names (used for help text)
# ---------------------------------------------------------------------------

def get_enrolled_subjects(student_id: int) -> list[str]:
    """
    Return a list of subject names for this student.

    Used by student.py to show the user what subjects they can ask about.
    Derived from gap data so no extra query is needed.

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        Sorted list of subject name strings. Empty list if no data.
    """
    gaps = get_learning_gaps(student_id)
    return sorted(g["subject_name"] for g in gaps)
