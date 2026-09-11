"""
modules/analytics.py — SCMS Analytics & Reports Domain Module
==============================================================
Provides simple, deterministic aggregation and reporting for SCMS data.

This is a DOMAIN module. It:
  - Queries SQLite via database.get_connection()
  - Performs read-only aggregations and statistical calculations
  - Returns data as plain Python dictionaries/lists
  - Reuses ATTENDANCE_THRESHOLD from modules.attendance
  - Contains no interactive terminal prompts
  - Pure read-only queries with zero mutations

Architecture:
  main.py → teacher_menu() / admin_menu()
                → modules/analytics.py → database.py → SQLite

Reports supported:
  1. Dashboard Summary (system-wide vital statistics)
  2. Attendance Analytics (overall, below/above threshold, subject-wise)
  3. Performance Analytics (overall, below/above threshold, subject-wise)
  4. Student Performance Summary (per-student attendance & marks status)
  5. Resource Usage Statistics (inventory status & booking counts)
  6. Safety Alert Statistics (status breakdown & counts by type)
"""

from database import get_connection
from modules.attendance import ATTENDANCE_THRESHOLD
from modules.marks import PERFORMANCE_THRESHOLD


# ---------------------------------------------------------------------------
# 1. Attendance Analytics
# ---------------------------------------------------------------------------

def get_attendance_analytics() -> dict:
    """
    Compute aggregate attendance statistics across the institution.

    Reuses ATTENDANCE_THRESHOLD from modules.attendance (75%).

    Returns:
        Dictionary containing:
        - total_students: Total enrolled students in the database
        - total_records: Total attendance rows logged
        - overall_percentage: Institution-wide attendance percentage
        - below_threshold: Number of students with attendance < threshold
        - above_or_equal_threshold: Number of students with attendance >= threshold
        - threshold: The attendance threshold (75.0)
        - subject_attendance: List of per-subject attendance dictionaries
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Total enrolled students
        cursor.execute("SELECT COUNT(*) AS total FROM students")
        total_students = cursor.fetchone()["total"]

        # Total attendance records and present count
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count
            FROM attendance
            """
        )
        overall_row = cursor.fetchone()
        total_records = overall_row["total"]
        present_count = overall_row["present_count"] or 0

        if total_records > 0:
            overall_percentage = (present_count / total_records) * 100.0
        else:
            overall_percentage = 0.0

        # Per-student attendance distribution
        cursor.execute(
            """
            SELECT
                student_id,
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count
            FROM attendance
            GROUP BY student_id
            """
        )
        student_rows = cursor.fetchall()

        below_threshold = 0
        above_or_equal_threshold = 0

        for row in student_rows:
            if row["total"] > 0:
                pct = (row["present_count"] / row["total"]) * 100.0
                if pct < ATTENDANCE_THRESHOLD:
                    below_threshold += 1
                else:
                    above_or_equal_threshold += 1

        # Subject-wise attendance aggregation
        cursor.execute(
            """
            SELECT
                s.name AS subject_name,
                COUNT(a.id) AS total,
                SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count
            FROM subjects s
            JOIN attendance a ON s.id = a.subject_id
            GROUP BY s.name
            ORDER BY s.name
            """
        )
        subj_rows = cursor.fetchall()
        subject_attendance = []
        for r in subj_rows:
            tot = r["total"]
            pres = r["present_count"] or 0
            pct = (pres / tot * 100.0) if tot > 0 else 0.0
            subject_attendance.append({
                "subject_name": r["subject_name"],
                "total": tot,
                "present": pres,
                "attendance_percentage": pct,
            })

        return {
            "total_students": total_students,
            "total_records": total_records,
            "overall_percentage": overall_percentage,
            "below_threshold": below_threshold,
            "above_or_equal_threshold": above_or_equal_threshold,
            "threshold": ATTENDANCE_THRESHOLD,
            "subject_attendance": subject_attendance,
        }

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. Performance Analytics
# ---------------------------------------------------------------------------

def get_performance_analytics() -> dict:
    """
    Compute aggregate academic performance statistics across the institution.

    Formula: SUM(marks_obtained) / SUM(max_marks) * 100
    Reuses PERFORMANCE_THRESHOLD from modules.marks (50%).

    Returns:
        Dictionary containing:
        - total_students_with_marks: Number of unique students with marks records
        - overall_percentage: Institution-wide performance percentage
        - below_threshold: Number of students with performance < threshold
        - above_or_equal_threshold: Number of students with performance >= threshold
        - threshold: The performance threshold (50.0)
        - subject_performance: List of per-subject performance dictionaries
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Total unique students with marks
        cursor.execute("SELECT COUNT(DISTINCT student_id) AS total FROM marks")
        total_students_with_marks = cursor.fetchone()["total"]

        # Aggregate marks totals
        cursor.execute(
            """
            SELECT
                SUM(marks_obtained) AS total_obtained,
                SUM(max_marks) AS total_max
            FROM marks
            """
        )
        totals = cursor.fetchone()
        tot_obtained = totals["total_obtained"] or 0.0
        tot_max = totals["total_max"] or 0.0

        if tot_max > 0:
            overall_percentage = (tot_obtained / tot_max) * 100.0
        else:
            overall_percentage = 0.0

        # Per-student performance distribution
        cursor.execute(
            """
            SELECT
                student_id,
                SUM(marks_obtained) AS obtained,
                SUM(max_marks) AS max_m
            FROM marks
            GROUP BY student_id
            """
        )
        student_rows = cursor.fetchall()

        below_threshold = 0
        above_or_equal_threshold = 0

        for r in student_rows:
            if r["max_m"] and r["max_m"] > 0:
                pct = (r["obtained"] / r["max_m"]) * 100.0
                if pct < PERFORMANCE_THRESHOLD:
                    below_threshold += 1
                else:
                    above_or_equal_threshold += 1

        # Subject-wise performance aggregation
        cursor.execute(
            """
            SELECT
                s.name AS subject_name,
                SUM(m.marks_obtained) AS total_obtained,
                SUM(m.max_marks) AS total_max
            FROM subjects s
            JOIN marks m ON s.id = m.subject_id
            GROUP BY s.name
            ORDER BY s.name
            """
        )
        subj_rows = cursor.fetchall()
        subject_performance = []
        for r in subj_rows:
            obt = r["total_obtained"] or 0.0
            mx = r["total_max"] or 0.0
            pct = (obt / mx * 100.0) if mx > 0 else 0.0
            subject_performance.append({
                "subject_name": r["subject_name"],
                "obtained": obt,
                "maximum": mx,
                "performance_percentage": pct,
            })

        return {
            "total_students_with_marks": total_students_with_marks,
            "overall_percentage": overall_percentage,
            "below_threshold": below_threshold,
            "above_or_equal_threshold": above_or_equal_threshold,
            "threshold": PERFORMANCE_THRESHOLD,
            "subject_performance": subject_performance,
        }

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 3. Student Performance Summary
# ---------------------------------------------------------------------------

def get_student_performance_summary() -> list[dict]:
    """
    Return an individual row for every enrolled student combining both
    their overall attendance and performance percentages.

    If attendance or marks data is missing for a student, percentage is None
    and status is 'NO DATA' (missing data is never treated as 0).

    Returns:
        List of dictionaries with student performance metrics.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                st.id AS student_id,
                u.name AS student_name,
                st.roll_number,
                c.class_name
            FROM students st
            JOIN users u ON st.user_id = u.id
            JOIN classes c ON st.class_id = c.id
            ORDER BY st.roll_number
            """
        )
        students = cursor.fetchall()

        summary_list = []

        for s in students:
            student_id = s["student_id"]

            # ── Attendance for this student ─────────────────────────────────
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count
                FROM attendance
                WHERE student_id = ?
                """,
                (student_id,)
            )
            att_row = cursor.fetchone()
            if att_row and att_row["total"] > 0:
                att_pct = (att_row["present_count"] / att_row["total"]) * 100.0
                att_status = "GOOD" if att_pct >= ATTENDANCE_THRESHOLD else "LOW"
            else:
                att_pct = None
                att_status = "NO DATA"

            # ── Performance for this student ────────────────────────────────
            cursor.execute(
                """
                SELECT
                    SUM(marks_obtained) AS obtained,
                    SUM(max_marks) AS max_m
                FROM marks
                WHERE student_id = ?
                """,
                (student_id,)
            )
            marks_row = cursor.fetchone()
            if marks_row and marks_row["max_m"] and marks_row["max_m"] > 0:
                perf_pct = (marks_row["obtained"] / marks_row["max_m"]) * 100.0
                perf_status = "GOOD" if perf_pct >= PERFORMANCE_THRESHOLD else "NEEDS IMPROVEMENT"
            else:
                perf_pct = None
                perf_status = "NO DATA"

            summary_list.append({
                "student_id": student_id,
                "name": s["student_name"],
                "student_name": s["student_name"],
                "roll_number": s["roll_number"],
                "class_name": s["class_name"],
                "attendance_percentage": att_pct,
                "attendance_status": att_status,
                "performance_percentage": perf_pct,
                "performance_status": perf_status,
            })

        return summary_list

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. Resource Usage Analytics
# ---------------------------------------------------------------------------

def get_resource_analytics() -> dict:
    """
    Calculate classroom resource inventory and booking usage statistics.

    Note: The database tracks bookings, not time duration. Metrics represent
    booking counts and inventory status.

    Returns:
        Dictionary containing:
        - total_resources: Count of all cataloged resources
        - available: Count of resources with status 'Available'
        - in_use: Count of resources with status 'In Use'
        - maintenance: Count of resources with status 'Maintenance'
        - total_bookings: Total booking records created
        - active_bookings: Bookings currently open (returned_at IS NULL)
        - completed_bookings: Bookings finished (returned_at IS NOT NULL)
        - booking_counts: List of booking counts per resource
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Resource status counts
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) AS available_count,
                SUM(CASE WHEN status = 'In Use' THEN 1 ELSE 0 END) AS in_use_count,
                SUM(CASE WHEN status = 'Maintenance' THEN 1 ELSE 0 END) AS maintenance_count
            FROM resources
            """
        )
        res_row = cursor.fetchone()
        total_resources = res_row["total"] or 0
        available = res_row["available_count"] or 0
        in_use = res_row["in_use_count"] or 0
        maintenance = res_row["maintenance_count"] or 0

        # Booking counts
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_bookings,
                SUM(CASE WHEN returned_at IS NULL THEN 1 ELSE 0 END) AS active_bookings,
                SUM(CASE WHEN returned_at IS NOT NULL THEN 1 ELSE 0 END) AS completed_bookings
            FROM bookings
            """
        )
        b_row = cursor.fetchone()
        total_bookings = b_row["total_bookings"] or 0
        active_bookings = b_row["active_bookings"] or 0
        completed_bookings = b_row["completed_bookings"] or 0

        # Booking count by resource
        cursor.execute(
            """
            SELECT
                r.resource_code,
                r.name AS resource_name,
                COUNT(b.id) AS booking_count
            FROM resources r
            LEFT JOIN bookings b ON r.id = b.resource_id
            GROUP BY r.id, r.resource_code, r.name
            ORDER BY booking_count DESC, r.resource_code
            """
        )
        rows = cursor.fetchall()
        booking_counts = []
        for r in rows:
            booking_counts.append({
                "resource_code": r["resource_code"],
                "resource_name": r["resource_name"],
                "name": r["resource_name"],
                "booking_count": r["booking_count"],
            })

        return {
            "total_resources": total_resources,
            "available": available,
            "in_use": in_use,
            "maintenance": maintenance,
            "total_bookings": total_bookings,
            "active_bookings": active_bookings,
            "completed_bookings": completed_bookings,
            "booking_counts": booking_counts,
        }

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 5. Safety Alert Analytics
# ---------------------------------------------------------------------------

def get_alert_analytics() -> dict:
    """
    Calculate safety and security alert statistics.

    Returns:
        Dictionary containing:
        - total_alerts: Total alerts recorded
        - active_alerts: Alerts with status 'Active'
        - resolved_alerts: Alerts with status 'Resolved'
        - by_type: Dictionary mapping each alert type to its occurrence count
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Overall alert counts
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_alerts,
                SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active_alerts,
                SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved_alerts
            FROM alerts
            """
        )
        row = cursor.fetchone()
        total_alerts = row["total_alerts"] or 0
        active_alerts = row["active_alerts"] or 0
        resolved_alerts = row["resolved_alerts"] or 0

        # Counts by alert type
        counts_by_type = {
            "Fire": 0,
            "Unauthorized Access": 0,
            "Medical": 0,
            "Other": 0,
        }

        cursor.execute(
            """
            SELECT alert_type, COUNT(*) AS count
            FROM alerts
            GROUP BY alert_type
            """
        )
        type_rows = cursor.fetchall()
        for tr in type_rows:
            if tr["alert_type"] in counts_by_type:
                counts_by_type[tr["alert_type"]] = tr["count"]

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "resolved_alerts": resolved_alerts,
            "by_type": counts_by_type,
        }

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 6. Overall Dashboard Summary
# ---------------------------------------------------------------------------

def get_dashboard_summary() -> dict:
    """
    Return high-level vital metrics across the entire classroom management system:
      - total_students
      - total_teachers
      - total_resources
      - active_resource_bookings
      - low_attendance_students
      - low_performance_students
      - active_safety_alerts

    Reuses existing analytics domain logic.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Total enrolled students
        cursor.execute("SELECT COUNT(*) AS total FROM students")
        total_students = cursor.fetchone()["total"] or 0

        # Total teachers
        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'teacher'")
        total_teachers = cursor.fetchone()["total"] or 0

        # Total resources
        cursor.execute("SELECT COUNT(*) AS total FROM resources")
        total_resources = cursor.fetchone()["total"] or 0

        # Active resource bookings
        cursor.execute("SELECT COUNT(*) AS total FROM bookings WHERE returned_at IS NULL")
        active_bookings = cursor.fetchone()["total"] or 0

        # Active safety alerts
        cursor.execute("SELECT COUNT(*) AS total FROM alerts WHERE status = 'Active'")
        active_alerts = cursor.fetchone()["total"] or 0

    finally:
        conn.close()

    # Re-use threshold logic from attendance and performance analytics
    att_analytics = get_attendance_analytics()
    low_attendance_students = att_analytics["below_threshold"]

    perf_analytics = get_performance_analytics()
    low_performance_students = perf_analytics["below_threshold"]

    return {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_resources": total_resources,
        "active_resource_bookings": active_bookings,
        "low_attendance_students": low_attendance_students,
        "low_performance_students": low_performance_students,
        "active_safety_alerts": active_alerts,
    }
