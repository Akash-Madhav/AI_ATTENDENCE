# services/student_service.py

import os
import shutil
from db.db import get_connection
from engine.face_engine import get_face_engine
from config import CONFIG

engine = get_face_engine()


def register_student(name: str, reg_no: str, department: str, photo_paths: list) -> int:
    """
    Register a new student with N reference photos.
    Returns the new student_id on success, raises on failure.
    """
    if len(photo_paths) < 1:
        raise ValueError("At least 1 reference photo required.")

    # 1. Encode all provided photos
    all_encodings = []
    for path in photo_paths:
        encs = engine.encode_from_path(path)
        if not encs:
            raise ValueError(f"No face detected in: {os.path.basename(path)}")
        all_encodings.append(encs[0])

    # 2. Average into representative vector
    representative = engine.average_encodings(all_encodings)
    encoding_blob = engine.serialise(representative)

    # 3. Copy primary photo to asset store
    asset_dir = CONFIG["PHOTO_STORE"]
    os.makedirs(asset_dir, exist_ok=True)
    dest_photo = os.path.join(asset_dir, f"{reg_no}.jpg")
    shutil.copy(photo_paths[0], dest_photo)

    # 4. Persist to DB
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (reg_no, name, department, photo_path) VALUES (%s, %s, %s, %s)",
            (reg_no, name, department, dest_photo)
        )
        student_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO face_encodings (student_id, encoding) VALUES (%s, %s)",
            (student_id, encoding_blob)
        )
        conn.commit()

    # 5. Rebuild KDTree index
    _rebuild_index()
    return student_id


def get_all_students() -> list:
    """Return all students as list of dicts."""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, reg_no, name, department, photo_path, created_at FROM students ORDER BY name")
        return cursor.fetchall()


def delete_student(student_id: int):
    """Delete student (CASCADE removes encodings and attendance records)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        conn.commit()
    _rebuild_index()


def load_all_encodings() -> list:
    """Load all (student_id, encoding) pairs from DB for KDTree."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, encoding FROM face_encodings")
        rows = cursor.fetchall()
    return [(sid, engine.deserialise(blob)) for sid, blob in rows]


def _rebuild_index():
    """Rebuild KDTree after any registration/deletion."""
    pairs = load_all_encodings()
    engine.build_index(pairs)
