"""
modules/learning_gap.py — SCMS Learning Gap Detection
======================================================
Identifies subjects where a student may need additional attention.

This is a RULE-BASED system. It:
  - Retrieves subject attendance and performance data for a student
  - Applies explicit IF/ELSE rules to classify each subject
  - Returns structured gap information with priority and recommendations
  - Contains no user-input calls, menus, or print() statements

It is NOT:
  - Machine learning
  - AI or generative AI
  - Predictive modelling
  - An external API call

Every result is deterministic: the same data always produces the same output.

Architecture:
  student.py → get_learning_gaps(student_id) → [attendance + marks queries]
                                              → database.py → SQLite

Threshold reuse:
  Attendance threshold (75.0) is imported from modules.attendance.
  Performance threshold (50.0) is imported from modules.marks.
  There is ONE source of truth for each threshold.

Subject matching:
  Subjects are matched by subject_id (their database primary key), NOT by
  name string. The same subject name can exist in multiple classes:
      Mathematics → BCA-A (subject_id=1)
      Mathematics → BCA-B (subject_id=4)
  Matching by subject_id prevents cross-class confusion.

  To obtain subject_id alongside the attendance/performance percentages,
  this module contains two small internal queries (_get_att_by_subject_id
  and _get_perf_by_subject_id). These do NOT replace or modify the public
  functions in attendance.py/marks.py — those remain unchanged for the
  existing student.py display features.
"""

from database import get_connection
from modules.attendance import ATTENDANCE_THRESHOLD
from modules.marks import PERFORMANCE_THRESHOLD


# ---------------------------------------------------------------------------
# Status labels (reuse thresholds imported above)
# ---------------------------------------------------------------------------

# These string constants mirror what attendance.py and marks.py produce.
# Using named constants avoids scattered magic strings.
ATT_LOW  = "LOW"
ATT_GOOD = "GOOD"
ATT_NONE = "NO DATA"

PERF_NI   = "NEEDS IMPROVEMENT"
PERF_GOOD = "GOOD"
PERF_NONE = "NO DATA"


# ---------------------------------------------------------------------------
# Internal data fetchers (subject_id-keyed)
# ---------------------------------------------------------------------------

def _get_att_by_subject_id(student_id: int) -> dict[int, dict]:
    """
    Return attendance stats keyed by subject_id.

    Why not reuse get_subject_attendance() from attendance.py?
        That function returns dicts keyed by subject_name, which is not
        reliable for matching when the same name exists in different classes.
        This internal helper returns the same data but includes subject_id
        as the dict key, enabling correct cross-dataset matching.

    Returns:
        { subject_id: { subject_name, percentage, status }, ... }
        Empty dict if no attendance records exist.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                attendance.subject_id,
                subjects.name                                             AS subject_name,
                SUM(CASE WHEN attendance.status = 'Present' THEN 1
                         ELSE 0 END)                                      AS present,
                COUNT(*)                                                   AS total
            FROM attendance
            JOIN subjects ON attendance.subject_id = subjects.id
            WHERE attendance.student_id = ?
            GROUP BY attendance.subject_id
            """,
            (student_id,)
        ).fetchall()
    finally:
        conn.close()

    result = {}
    for row in rows:
        total   = row["total"]
        present = row["present"]
        pct     = (present / total * 100) if total > 0 else 0.0
        # Reuse the imported threshold to determine status.
        status  = ATT_GOOD if pct >= ATTENDANCE_THRESHOLD else ATT_LOW
        result[row["subject_id"]] = {
            "subject_name": row["subject_name"],
            "percentage"  : pct,
            "status"      : status,
        }
    return result


def _get_perf_by_subject_id(student_id: int) -> dict[int, dict]:
    """
    Return performance stats keyed by subject_id.

    Mirrors _get_att_by_subject_id but queries the marks table.
    Uses SUM(obtained)/SUM(max) — the same weighted calculation as marks.py.

    Returns:
        { subject_id: { subject_name, percentage, status }, ... }
        Empty dict if no marks records exist.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                marks.subject_id,
                subjects.name              AS subject_name,
                SUM(marks.marks_obtained)  AS obtained,
                SUM(marks.max_marks)       AS maximum
            FROM marks
            JOIN subjects ON marks.subject_id = subjects.id
            WHERE marks.student_id = ?
            GROUP BY marks.subject_id
            """,
            (student_id,)
        ).fetchall()
    finally:
        conn.close()

    result = {}
    for row in rows:
        maximum  = row["maximum"]
        obtained = row["obtained"]
        pct      = (obtained / maximum * 100) if maximum and maximum > 0 else 0.0
        # Reuse the imported threshold to determine status.
        status   = PERF_GOOD if pct >= PERFORMANCE_THRESHOLD else PERF_NI
        result[row["subject_id"]] = {
            "subject_name": row["subject_name"],
            "percentage"  : pct,
            "status"      : status,
        }
    return result


# ---------------------------------------------------------------------------
# Priority rules
# ---------------------------------------------------------------------------

def _compute_priority(att_status: str, perf_status: str) -> tuple[bool, str]:
    """
    Apply the learning-gap priority rules to two status labels.

    Rules:
        att=LOW  AND perf=NI   → gap=True,  priority="HIGH"
        att=LOW  AND perf=GOOD → gap=True,  priority="MEDIUM"
        att=GOOD AND perf=NI   → gap=True,  priority="MEDIUM"
        att=GOOD AND perf=GOOD → gap=False, priority="NONE"

    NO DATA handling:
        NO DATA is treated as "not a problem" — it is not counted as LOW
        or NI. Priority is determined only from the available category.
        If BOTH are NO DATA → gap=False, priority="NONE".

    Parameters:
        att_status  — ATT_LOW | ATT_GOOD | ATT_NONE
        perf_status — PERF_NI | PERF_GOOD | PERF_NONE

    Returns:
        (gap_exists: bool, priority: str)
    """
    att_low  = att_status  == ATT_LOW
    perf_bad = perf_status == PERF_NI

    if att_low and perf_bad:
        return True, "HIGH"
    elif att_low or perf_bad:
        return True, "MEDIUM"
    else:
        # Both GOOD, or one/both are NO DATA (not counted as a problem)
        return False, "NONE"


# ---------------------------------------------------------------------------
# Recommendation generator
# ---------------------------------------------------------------------------

def _get_recommendation(subject_name: str, att_status: str, perf_status: str) -> str:
    """
    Return a fixed, deterministic recommendation based on the gap flags.

    These messages are rule-based — not AI-generated, not random.

    Returns:
        A recommendation string.
    """
    att_low  = att_status  == ATT_LOW
    perf_bad = perf_status == PERF_NI

    if att_low and perf_bad:
        return (
            f"Attend {subject_name} classes regularly and "
            f"review the subject topics."
        )
    elif att_low:
        return f"Attend {subject_name} classes more regularly."
    elif perf_bad:
        return f"Review {subject_name} topics and practice more problems."
    else:
        return "No immediate learning gap detected."


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def get_learning_gaps(student_id: int) -> list[dict]:
    """
    Analyse a student's subjects and return learning gap information.

    Steps:
      1. Fetch attendance data keyed by subject_id.
      2. Fetch performance data keyed by subject_id.
      3. Build a union of all subject_ids seen in either dataset.
      4. For each subject, combine available data and apply rules.
      5. Return one dict per subject, sorted by priority then name.

    Matching by subject_id (not subject name):
      A student in BCA-A and a student in BCA-B both study "Mathematics"
      but their subject_ids are different. Using subject_id ensures we
      never confuse data from one class's Mathematics with another's.

    Missing-data handling:
      If a subject appears in attendance but not marks → performance = NO DATA.
      If a subject appears in marks but not attendance → attendance = NO DATA.
      Neither NO DATA case causes a crash or division by zero.

    Parameters:
        student_id — students.id (NOT users.id)

    Returns:
        List of dicts, one per subject. Empty list if no data at all.
        Each dict:
            subject_id              int
            subject_name            str
            attendance_percentage   float | None
            attendance_status       str   ("LOW" | "GOOD" | "NO DATA")
            performance_percentage  float | None
            performance_status      str   ("NEEDS IMPROVEMENT" | "GOOD" | "NO DATA")
            learning_gap            bool
            priority                str   ("HIGH" | "MEDIUM" | "NONE")
            recommendation          str
    """
    att_data  = _get_att_by_subject_id(student_id)   # { subject_id: {...} }
    perf_data = _get_perf_by_subject_id(student_id)  # { subject_id: {...} }

    # Union of all subject IDs seen in either dataset.
    all_subject_ids = sorted(set(att_data) | set(perf_data))

    if not all_subject_ids:
        return []

    results = []

    for sid in all_subject_ids:
        att  = att_data.get(sid)   # None if this subject has no attendance data
        perf = perf_data.get(sid)  # None if this subject has no marks data

        # Determine subject name: prefer attendance data, fall back to marks.
        subject_name = (att or perf)["subject_name"]

        # Extract values, using NO DATA sentinels when data is absent.
        att_pct    = att["percentage"]  if att  else None
        att_status = att["status"]      if att  else ATT_NONE

        perf_pct    = perf["percentage"] if perf else None
        perf_status = perf["status"]     if perf else PERF_NONE

        # Apply learning-gap rules.
        gap_exists, priority = _compute_priority(att_status, perf_status)

        # Generate deterministic recommendation.
        recommendation = _get_recommendation(subject_name, att_status, perf_status)

        results.append({
            "subject_id"            : sid,
            "subject_name"          : subject_name,
            "attendance_percentage" : att_pct,
            "attendance_status"     : att_status,
            "performance_percentage": perf_pct,
            "performance_status"    : perf_status,
            "learning_gap"          : gap_exists,
            "priority"              : priority,
            "recommendation"        : recommendation,
        })

    # Sort: HIGH first, then MEDIUM, then NONE; alphabetical within each group.
    priority_order = {"HIGH": 0, "MEDIUM": 1, "NONE": 2}
    results.sort(key=lambda r: (priority_order[r["priority"]], r["subject_name"]))

    return results
