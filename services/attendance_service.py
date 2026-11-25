# services/attendance_service.py

import cv2
import numpy as np
from datetime import date, datetime
from db.db import get_connection
from engine.face_engine import get_face_engine
from services.student_service import get_all_students, load_all_encodings
import pandas as pd

engine = get_face_engine()


def initialise_engine():
    """Call once at app startup to load encodings into KDTree."""
    pairs = load_all_encodings()
    engine.build_index(pairs)


def take_attendance(
    image_path: str,
    subject: str,
    class_name: str,
) -> dict:
    """
    Core attendance function.
    1. Runs classroom analysis.
    2. Identifies present students.
    3. Determines absent students (all_students - present).
    4. Persists session + records to DB.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    all_students = get_all_students()
    all_ids = {s["id"]: s for s in all_students}

    # Run AI pipeline
    result = engine.analyse_classroom(img, all_students)
    present_ids = {r["student_id"] for r in result["present"]}
    absent_ids = set(all_ids.keys()) - present_ids

    today = date.today()
    now = datetime.now().strftime("%H:%M:%S")

    # Persist session
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO attendance_sessions (subject, class_name, session_date, session_time, image_path)
               VALUES (%s, %s, %s, %s, %s)""",
            (subject, class_name, today, now, image_path)
        )
        session_id = cursor.lastrowid

        # Insert present records
        for r in result["present"]:
            cursor.execute(
                """INSERT IGNORE INTO attendance_records (session_id, student_id, status, confidence)
                   VALUES (%s, %s, 'present', %s)""",
                (session_id, r["student_id"], r["confidence"])
            )

        # Insert absent records
        for sid in absent_ids:
            cursor.execute(
                """INSERT IGNORE INTO attendance_records (session_id, student_id, status, confidence)
                   VALUES (%s, %s, 'absent', NULL)""",
                (session_id, sid)
            )

        conn.commit()

    # Build human-readable result
    present_students = [
        {**all_ids[r["student_id"]], "confidence": r["confidence"]}
        for r in result["present"] if r["student_id"] in all_ids
    ]
    absent_students = [all_ids[sid] for sid in absent_ids]

    return {
        "session_id":       session_id,
        "subject":          subject,
        "class_name":       class_name,
        "date":             str(today),
        "time":             now,
        "present":          present_students,
        "absent":           absent_students,
        "unknown_count":    len(result["unknown"]),
        "annotated_img":    result["annotated_img"],
        "total_students":   len(all_students),
        "present_count":    len(present_students),
        "absent_count":     len(absent_students),
    }


def get_report(from_date: str = None, to_date: str = None, subject: str = None) -> pd.DataFrame:
    """
    Generate an attendance report as a Pandas DataFrame.
    Filterable by date range and/or subject.
    """
    query = """
        SELECT
            s.reg_no,
            s.name,
            s.department,
            sess.subject,
            sess.class_name,
            sess.session_date,
            sess.session_time,
            ar.status,
            ROUND(ar.confidence * 100, 1) AS confidence_pct
        FROM attendance_records ar
        JOIN students s ON ar.student_id = s.id
        JOIN attendance_sessions sess ON ar.session_id = sess.id
        WHERE 1=1
    """
    params = []
    if from_date:
        query += " AND sess.session_date >= %s"
        params.append(from_date)
    if to_date:
        query += " AND sess.session_date <= %s"
        params.append(to_date)
    if subject:
        query += " AND sess.subject = %s"
        params.append(subject)

    query += " ORDER BY sess.session_date DESC, sess.session_time DESC, s.name"

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def export_report_excel(df: pd.DataFrame, output_path: str):
    df.to_excel(output_path, index=False, engine="openpyxl")
