# AI-Based Classroom Attendance System — Implementation Blueprint

> **Project:** U24AD401 | AI Attendance via Computer Vision  
> **Team:** Akashmadhav Y · Allocious Franklin R · Ananthram A  
> **Stack:** Python · MediaPipe · face_recognition (dlib) · MySQL · Tkinter  
> **Architecture:** Desktop MVP — Tkinter UI → Python Service Layer → MySQL

---

## Table of Contents

1. [Architecture Decision Record](#1-architecture-decision-record)
2. [Tech Stack — Final Choices & Rationale](#2-tech-stack--final-choices--rationale)
3. [System Workflow](#3-system-workflow)
4. [Project File Structure](#4-project-file-structure)
5. [Database Schema](#5-database-schema)
6. [Module Breakdown & Implementation](#6-module-breakdown--implementation)
   - [6.1 Database Layer](#61-database-layer-dbpy)
   - [6.2 Face Engine](#62-face-engine-face_enginepy)
   - [6.3 Student Service](#63-student-service-student_servicepy)
   - [6.4 Attendance Service](#64-attendance-service-attendance_servicepy)
   - [6.5 Tkinter App — Main Window](#65-tkinter-app--main-window-apppy)
   - [6.6 Register Student Screen](#66-register-student-screen-ui_registrationpy)
   - [6.7 Take Attendance Screen](#67-take-attendance-screen-ui_attendancepy)
   - [6.8 Reports Screen](#68-reports-screen-ui_reportspy)
7. [Environment Setup](#7-environment-setup)
8. [MySQL Bootstrap Script](#8-mysql-bootstrap-script)
9. [Configuration File](#9-configuration-file)
10. [Accuracy & Tuning Notes](#10-accuracy--tuning-notes)
11. [Known Limitations & Future Scope](#11-known-limitations--future-scope)

---

## 1. Architecture Decision Record

### Why No Flask?

The original PPT proposes a Flask REST API. For a **desktop MVP** with Tkinter as the sole consumer, Flask adds network overhead and a second process to manage with zero benefit. The service layer (Python classes) acts as the "API" internally. Flask makes sense only when a web/mobile frontend is added later — that refactor is trivial since the service layer already has clean method boundaries.

### Why MediaPipe + face_recognition Together?

| Stage | Tool | Why |
|-------|------|-----|
| **Face Detection** | MediaPipe FaceDetection | Runs on CPU, handles multiple faces, very fast (~30ms per frame), excellent on classroom angles |
| **Face Encoding** | `face_recognition` (dlib) | Industry-standard 128-dimension embedding, tolerates lighting variation, ~99.38% accuracy on LFW benchmark |
| **Vector Matching** | NumPy / SciPy KDTree | Euclidean distance with configurable threshold; KDTree indexing for fast lookup when student count grows |

### Why Not Tesseract?

Tesseract is an **OCR engine** (converts image → text). It has no application in face recognition. It was likely confused with face recognition libraries. It is not part of this system.

### Why Not DeepFace or MTCNN?

- **DeepFace** is heavier, slower on CPU, harder to install. Good for Phase 2 custom CNN work.
- **MTCNN** is a detection-only model — no encoding. We'd still need dlib. Adds complexity.
- MediaPipe + face_recognition is the cleanest MVP combo — proven, lightweight, pip-installable.

---

## 2. Tech Stack — Final Choices & Rationale

```
Python 3.10+
├── Core AI / Vision
│   ├── mediapipe           # Face detection bounding boxes
│   ├── face_recognition    # dlib-backed 128-dim face encodings
│   ├── opencv-python       # Image I/O, preprocessing, drawing
│   └── numpy               # Vector math, distance calculations
│
├── Database
│   ├── mysql-connector-python   # MySQL driver
│   └── MySQL 8.x               # Storage: students, encodings, sessions, attendance
│
├── Frontend
│   ├── tkinter             # Bundled with Python — no install needed
│   ├── Pillow (PIL)        # Image display inside Tkinter
│   └── ttkbootstrap        # Modern themed widgets (replaces plain ttk)
│
└── Utilities
    ├── python-dotenv       # Config from .env file
    ├── pandas              # Attendance report generation
    └── openpyxl            # Excel export of reports
```

---

## 3. System Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REGISTRATION FLOW (One-time per student)          │
│                                                                       │
│  User uploads 3-5 photos of student                                  │
│       │                                                               │
│       ▼                                                               │
│  [MediaPipe] Detect face bounding box in each photo                  │
│       │                                                               │
│       ▼                                                               │
│  [face_recognition] Generate 128-dim encoding for each photo         │
│       │                                                               │
│       ▼                                                               │
│  Average the N encodings → 1 representative encoding vector          │
│       │                                                               │
│       ▼                                                               │
│  Store: students table (name, reg_no, dept, photo_path)              │
│         encodings table (student_id, encoding BLOB)                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    ATTENDANCE FLOW (Per session)                      │
│                                                                       │
│  Teacher selects/captures classroom photo                             │
│       │                                                               │
│       ▼                                                               │
│  [OpenCV] Preprocess: resize, normalize, CLAHE histogram equalise    │
│       │                                                               │
│       ▼                                                               │
│  [MediaPipe] Detect all face bounding boxes in classroom photo        │
│       │                                                               │
│       ▼  (for each detected face)                                     │
│  [face_recognition] Encode each cropped face → 128-dim vector        │
│       │                                                               │
│       ▼                                                               │
│  [SciPy KDTree] Query against all known student encodings             │
│       │   distance < threshold (0.5) → MATCH                         │
│       │   distance ≥ threshold       → UNKNOWN FACE                  │
│       ▼                                                               │
│  Build result: {present: [...], absent: [...], unknown_count: N}     │
│       │                                                               │
│       ▼                                                               │
│  Write to DB: attendance_sessions + attendance_records               │
│   (UNIQUE constraint on student_id + session_id prevents duplicates) │
│       │                                                               │
│       ▼                                                               │
│  Display annotated image + present/absent table in Tkinter           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Project File Structure

```
attendance-system/
│
├── .env                        # DB credentials, config (never commit)
├── requirements.txt
├── config.py                   # Loads .env, exposes CONFIG dict
│
├── db/
│   ├── __init__.py
│   ├── db.py                   # MySQLConnectionPool, get_connection()
│   └── schema.sql              # DDL — run once to bootstrap DB
│
├── engine/
│   ├── __init__.py
│   └── face_engine.py          # MediaPipe detection + face_recognition encoding + KDTree matching
│
├── services/
│   ├── __init__.py
│   ├── student_service.py      # register_student(), get_all_students(), delete_student()
│   └── attendance_service.py   # create_session(), take_attendance(), get_report()
│
├── ui/
│   ├── __init__.py
│   ├── app.py                  # Root Tkinter window, navigation sidebar
│   ├── ui_registration.py      # Student registration screen
│   ├── ui_attendance.py        # Take attendance screen
│   └── ui_reports.py           # View reports screen
│
├── assets/
│   ├── icons/                  # SVG/PNG icons for UI
│   └── student_photos/         # Stored reference photos
│
└── main.py                     # Entry point: python main.py
```

---

## 5. Database Schema

```sql
-- schema.sql

CREATE DATABASE IF NOT EXISTS attendance_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE attendance_db;

-- ─────────────────────────────────────────────
-- Students master table
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  reg_no      VARCHAR(20)  NOT NULL UNIQUE,
  name        VARCHAR(100) NOT NULL,
  department  VARCHAR(100) NOT NULL,
  photo_path  VARCHAR(255),             -- path to reference photo on disk
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- Face encodings (128-dim float32 stored as BLOB)
-- One student can have multiple source encodings
-- averaged into one representative vector at match time
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS face_encodings (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  student_id  INT NOT NULL,
  encoding    BLOB NOT NULL,            -- numpy float32 array serialised via pickle
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- Attendance sessions (one per class per day)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance_sessions (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  subject       VARCHAR(100) NOT NULL,
  class_name    VARCHAR(50)  NOT NULL,
  session_date  DATE         NOT NULL,
  session_time  TIME         NOT NULL,
  image_path    VARCHAR(255),           -- classroom photo used for this session
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- Attendance records (many per session)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance_records (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  session_id  INT NOT NULL,
  student_id  INT NOT NULL,
  status      ENUM('present', 'absent') NOT NULL DEFAULT 'present',
  confidence  FLOAT,                    -- 1 - distance (0.0 to 1.0)
  marked_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_session_student (session_id, student_id),  -- no duplicates
  FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- Indexes for report queries
-- ─────────────────────────────────────────────
CREATE INDEX idx_records_session   ON attendance_records(session_id);
CREATE INDEX idx_records_student   ON attendance_records(student_id);
CREATE INDEX idx_sessions_date     ON attendance_sessions(session_date);
```

**Key Design Decisions:**
- `face_encodings` is separate from `students` so multiple training photos produce multiple raw encodings — averaged at query build time into one KDTree
- `UNIQUE KEY uq_session_student` enforces the duplicate-prevention constraint at the database level (PPT calls this out explicitly)
- `confidence` stored as `1 - euclidean_distance` so higher = better match
- `BLOB` + `pickle` for encoding storage — simple and efficient for this scale; switch to pgvector or Pinecone in Phase 2

---

## 6. Module Breakdown & Implementation

---

### 6.1 Database Layer — `db/db.py`

```python
# db/db.py
import mysql.connector
from mysql.connector import pooling
from config import CONFIG

# Connection pool — reused across all service calls
_pool = pooling.MySQLConnectionPool(
    pool_name="attendance_pool",
    pool_size=5,
    host=CONFIG["DB_HOST"],
    port=int(CONFIG["DB_PORT"]),
    database=CONFIG["DB_NAME"],
    user=CONFIG["DB_USER"],
    password=CONFIG["DB_PASSWORD"],
    autocommit=False,
)

def get_connection():
    """Get a connection from the pool. Always use as context manager."""
    return _pool.get_connection()


# Usage pattern everywhere in services:
# with get_connection() as conn:
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute("SELECT ...")
#     conn.commit()
```

---

### 6.2 Face Engine — `engine/face_engine.py`

This is the core AI module. Handles detection, encoding, and matching.

```python
# engine/face_engine.py

import cv2
import numpy as np
import face_recognition
import mediapipe as mp
import pickle
from scipy.spatial import KDTree
from config import CONFIG

mp_face_detection = mp.solutions.face_detection


class FaceEngine:
    """
    Two-stage face pipeline:
      Stage 1 — MediaPipe: fast multi-face detection → bounding boxes
      Stage 2 — face_recognition (dlib): 128-dim encoding per face

    For matching: SciPy KDTree over all registered student encodings.
    Threshold: Euclidean distance < 0.5 → match  (tunable in config)
    """

    def __init__(self):
        self._detector = mp_face_detection.FaceDetection(
            model_selection=1,          # model 1 = full range (better for group shots)
            min_detection_confidence=0.6
        )
        self._kdtree = None             # Built on demand / after DB load
        self._student_ids = []          # Parallel list to KDTree leaf order
        self.threshold = float(CONFIG.get("MATCH_THRESHOLD", 0.5))

    # ── Encoding ──────────────────────────────────────────────────────

    def encode_image(self, image_bgr: np.ndarray) -> list[np.ndarray]:
        """
        Given a BGR image (from cv2.imread), return a list of 128-dim
        encodings — one per detected face. Empty list if no faces found.

        Uses MediaPipe for detection (bboxes) then face_recognition for encoding.
        """
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        preprocessed = self._preprocess(rgb)

        # Stage 1: MediaPipe detection → face locations for dlib
        locations = self._mediapipe_locations(preprocessed)

        if not locations:
            return []

        # Stage 2: dlib encodings at detected locations
        encodings = face_recognition.face_encodings(preprocessed, locations, num_jitters=2)
        return encodings

    def encode_from_path(self, image_path: str) -> list[np.ndarray]:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        return self.encode_image(img)

    def average_encodings(self, encodings: list[np.ndarray]) -> np.ndarray:
        """Average multiple encodings from several photos into one vector."""
        if not encodings:
            raise ValueError("No encodings to average")
        return np.mean(encodings, axis=0)

    # ── KDTree (matching index) ────────────────────────────────────────

    def build_index(self, student_encodings: list[tuple[int, np.ndarray]]):
        """
        Build the KDTree from (student_id, encoding) pairs loaded from DB.
        Call this once at startup and after any new registration.

        student_encodings: [(student_id, 128-dim np.ndarray), ...]
        """
        if not student_encodings:
            self._kdtree = None
            self._student_ids = []
            return

        self._student_ids = [sid for sid, _ in student_encodings]
        vectors = np.array([enc for _, enc in student_encodings], dtype=np.float32)
        self._kdtree = KDTree(vectors)

    def identify_face(self, encoding: np.ndarray) -> tuple[int | None, float]:
        """
        Query KDTree with one face encoding.
        Returns (student_id, confidence) or (None, 0.0) if no match.
        confidence = 1 - distance  →  higher is better
        """
        if self._kdtree is None:
            return None, 0.0

        distance, idx = self._kdtree.query(encoding)
        if distance < self.threshold:
            confidence = round(1.0 - distance, 4)
            return self._student_ids[idx], confidence
        return None, 0.0

    # ── Classroom Analysis ─────────────────────────────────────────────

    def analyse_classroom(
        self,
        image_bgr: np.ndarray,
        all_students: list[dict]
    ) -> dict:
        """
        Full pipeline for a classroom photo.

        Returns:
        {
            "present":      [{"student_id": int, "confidence": float, "bbox": (x,y,w,h)}, ...],
            "unknown":      [{"bbox": (x,y,w,h)}, ...],
            "annotated_img": np.ndarray  # BGR image with drawn boxes
        }
        """
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        preprocessed = self._preprocess(rgb)
        locations = self._mediapipe_locations(preprocessed)

        if not locations:
            annotated = image_bgr.copy()
            return {"present": [], "unknown": [], "annotated_img": annotated}

        encodings = face_recognition.face_encodings(preprocessed, locations, num_jitters=1)

        present = []
        unknown = []
        seen_ids = set()  # Prevent same student matched twice in one photo

        annotated = image_bgr.copy()

        for (top, right, bottom, left), encoding in zip(locations, encodings):
            student_id, confidence = self.identify_face(encoding)
            bbox = (left, top, right - left, bottom - top)

            if student_id and student_id not in seen_ids:
                seen_ids.add(student_id)
                present.append({"student_id": student_id, "confidence": confidence, "bbox": bbox})
                # Draw green box
                cv2.rectangle(annotated, (left, top), (right, bottom), (0, 200, 0), 2)
                label = f"ID:{student_id} ({confidence:.0%})"
                cv2.putText(annotated, label, (left, top - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 1)
            else:
                unknown.append({"bbox": bbox})
                # Draw red box
                cv2.rectangle(annotated, (left, top), (right, bottom), (0, 0, 220), 2)
                cv2.putText(annotated, "Unknown", (left, top - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 220), 1)

        return {"present": present, "unknown": unknown, "annotated_img": annotated}

    # ── Serialisation (for DB storage) ────────────────────────────────

    @staticmethod
    def serialise(encoding: np.ndarray) -> bytes:
        return pickle.dumps(encoding.astype(np.float32))

    @staticmethod
    def deserialise(blob: bytes) -> np.ndarray:
        return pickle.loads(blob)

    # ── Internal Helpers ───────────────────────────────────────────────

    def _preprocess(self, rgb: np.ndarray) -> np.ndarray:
        """
        Resize large images (keeps computation bounded),
        apply CLAHE on luminance channel for low-light resilience.
        """
        h, w = rgb.shape[:2]
        max_dim = 1280
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            rgb = cv2.resize(rgb, (int(w * scale), int(h * scale)))

        # CLAHE on L channel of LAB for contrast normalisation
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    def _mediapipe_locations(self, rgb: np.ndarray) -> list[tuple]:
        """
        Run MediaPipe FaceDetection and return locations in dlib format:
        list of (top, right, bottom, left) tuples — integers.
        """
        results = self._detector.process(rgb)
        if not results.detections:
            return []

        h, w = rgb.shape[:2]
        locations = []
        for det in results.detections:
            bb = det.location_data.relative_bounding_box
            x1 = max(0, int(bb.xmin * w))
            y1 = max(0, int(bb.ymin * h))
            x2 = min(w, int((bb.xmin + bb.width) * w))
            y2 = min(h, int((bb.ymin + bb.height) * h))
            locations.append((y1, x2, y2, x1))  # (top, right, bottom, left)

        return locations
```

---

### 6.3 Student Service — `services/student_service.py`

```python
# services/student_service.py

import os
import shutil
from db.db import get_connection
from engine.face_engine import FaceEngine
from config import CONFIG

engine = FaceEngine()


def register_student(name: str, reg_no: str, department: str, photo_paths: list[str]) -> int:
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
        all_encodings.append(encs[0])  # Take the first face in each photo

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


def get_all_students() -> list[dict]:
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


def load_all_encodings() -> list[tuple[int, object]]:
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
```

---

### 6.4 Attendance Service — `services/attendance_service.py`

```python
# services/attendance_service.py

import cv2
import numpy as np
from datetime import date, datetime
from db.db import get_connection
from engine.face_engine import FaceEngine
from services.student_service import get_all_students, load_all_encodings
import pandas as pd

engine = FaceEngine()


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

    Returns full result dict for UI consumption.
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
    present_students = [all_ids[r["student_id"]] | {"confidence": r["confidence"]}
                        for r in result["present"] if r["student_id"] in all_ids]
    absent_students  = [all_ids[sid] for sid in absent_ids]

    return {
        "session_id":       session_id,
        "subject":          subject,
        "class_name":       class_name,
        "date":             str(today),
        "time":             now,
        "present":          present_students,
        "absent":           absent_students,
        "unknown_count":    len(result["unknown"]),
        "annotated_img":    result["annotated_img"],   # numpy BGR array for display
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
```

---

### 6.5 Tkinter App — Main Window `ui/app.py`

```python
# ui/app.py

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from services.attendance_service import initialise_engine
from ui.ui_registration import RegistrationFrame
from ui.ui_attendance import AttendanceFrame
from ui.ui_reports import ReportsFrame


class AttendanceApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")       # ttkbootstrap dark theme
        self.title("AI Attendance System")
        self.geometry("1200x750")
        self.minsize(900, 600)
        self.resizable(True, True)

        # Load face encodings into KDTree at startup
        initialise_engine()

        self._build_layout()
        self._show_frame("attendance")

    def _build_layout(self):
        # ── Sidebar ────────────────────────────────────────────────────
        sidebar = ttk.Frame(self, width=220, bootstyle="dark")
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="🎓 AI Attendance", font=("Segoe UI", 13, "bold"),
                  bootstyle="inverse-dark").pack(pady=(24, 32), padx=16)

        nav_buttons = [
            ("📷  Take Attendance",  "attendance"),
            ("👤  Register Student", "registration"),
            ("📊  Reports",          "reports"),
        ]
        for label, key in nav_buttons:
            ttk.Button(sidebar, text=label, bootstyle="secondary-outline",
                       command=lambda k=key: self._show_frame(k),
                       width=22).pack(pady=6, padx=16)

        # ── Content area ───────────────────────────────────────────────
        self.content = ttk.Frame(self)
        self.content.pack(side=LEFT, fill=BOTH, expand=True)

        self._frames = {}
        for key, FrameClass in [
            ("attendance",   AttendanceFrame),
            ("registration", RegistrationFrame),
            ("reports",      ReportsFrame),
        ]:
            frame = FrameClass(self.content, self)
            frame.place(relwidth=1, relheight=1)
            self._frames[key] = frame

    def _show_frame(self, key: str):
        self._frames[key].tkraise()
        if hasattr(self._frames[key], "on_show"):
            self._frames[key].on_show()


def run():
    app = AttendanceApp()
    app.mainloop()
```

---

### 6.6 Register Student Screen — `ui/ui_registration.py`

```python
# ui/ui_registration.py

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from services.student_service import register_student, get_all_students, delete_student
import os


class RegistrationFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.photo_paths = []
        self.photo_labels = []
        self._build()

    def on_show(self):
        self._refresh_table()

    def _build(self):
        # ── Left panel: form ───────────────────────────────────────────
        left = ttk.Frame(self, width=380)
        left.pack(side=LEFT, fill=Y, padx=24, pady=24)
        left.pack_propagate(False)

        ttk.Label(left, text="Register New Student", font=("Segoe UI", 14, "bold")).pack(anchor=W, pady=(0, 16))

        # Form fields
        fields = [("Full Name", "name"), ("Reg Number", "reg_no"), ("Department", "dept")]
        self.vars = {}
        for label, key in fields:
            ttk.Label(left, text=label).pack(anchor=W, pady=(8, 2))
            var = tk.StringVar()
            ttk.Entry(left, textvariable=var, width=36).pack(anchor=W)
            self.vars[key] = var

        # Photo picker
        ttk.Label(left, text="Reference Photos (1–5)").pack(anchor=W, pady=(16, 4))
        self.photo_strip = ttk.Frame(left)
        self.photo_strip.pack(anchor=W)

        ttk.Button(left, text="+ Add Photos", bootstyle="secondary",
                   command=self._pick_photos).pack(anchor=W, pady=8)

        ttk.Button(left, text="Register Student", bootstyle="success",
                   command=self._submit, width=30).pack(pady=(16, 0))

        # ── Right panel: student table ─────────────────────────────────
        right = ttk.Frame(self)
        right.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 24), pady=24)

        ttk.Label(right, text="Registered Students", font=("Segoe UI", 14, "bold")).pack(anchor=W, pady=(0, 12))

        cols = ("reg_no", "name", "department", "registered")
        self.table = ttk.Treeview(right, columns=cols, show="headings", height=18, bootstyle="dark")
        for col, heading, width in zip(cols, ("Reg No", "Name", "Department", "Date"), (120, 200, 160, 120)):
            self.table.heading(col, text=heading)
            self.table.column(col, width=width)
        self.table.pack(fill=BOTH, expand=True)

        ttk.Button(right, text="🗑 Delete Selected", bootstyle="danger-outline",
                   command=self._delete_selected).pack(anchor=E, pady=8)

    def _pick_photos(self):
        paths = filedialog.askopenfilenames(
            title="Select student photos",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        self.photo_paths = list(paths)[:5]
        # Show thumbnails
        for w in self.photo_strip.winfo_children():
            w.destroy()
        for path in self.photo_paths:
            img = Image.open(path).resize((56, 56))
            tk_img = ImageTk.PhotoImage(img)
            lbl = ttk.Label(self.photo_strip, image=tk_img)
            lbl.image = tk_img
            lbl.pack(side=LEFT, padx=2)

    def _submit(self):
        name = self.vars["name"].get().strip()
        reg_no = self.vars["reg_no"].get().strip()
        dept = self.vars["dept"].get().strip()

        if not all([name, reg_no, dept]):
            messagebox.showerror("Error", "All fields are required.")
            return
        if not self.photo_paths:
            messagebox.showerror("Error", "Please select at least one photo.")
            return

        try:
            sid = register_student(name, reg_no, dept, self.photo_paths)
            messagebox.showinfo("Success", f"Student '{name}' registered (ID: {sid})")
            for var in self.vars.values():
                var.set("")
            self.photo_paths = []
            for w in self.photo_strip.winfo_children():
                w.destroy()
            self._refresh_table()
        except Exception as e:
            messagebox.showerror("Registration Failed", str(e))

    def _refresh_table(self):
        self.table.delete(*self.table.get_children())
        for s in get_all_students():
            self.table.insert("", END, iid=s["id"], values=(
                s["reg_no"], s["name"], s["department"],
                str(s["created_at"])[:10]
            ))

    def _delete_selected(self):
        selected = self.table.selection()
        if not selected:
            return
        if messagebox.askyesno("Confirm", "Delete selected student(s)? This cannot be undone."):
            for iid in selected:
                delete_student(int(iid))
            self._refresh_table()
```

---

### 6.7 Take Attendance Screen — `ui/ui_attendance.py`

```python
# ui/ui_attendance.py

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import threading
from services.attendance_service import take_attendance


class AttendanceFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.result = None
        self._build()

    def _build(self):
        # ── Top controls ───────────────────────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill=X, padx=24, pady=16)

        ttk.Label(top, text="Take Attendance", font=("Segoe UI", 14, "bold")).pack(side=LEFT)

        controls = ttk.Frame(top)
        controls.pack(side=RIGHT)

        ttk.Label(controls, text="Subject:").pack(side=LEFT, padx=(0, 4))
        self.subject_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=self.subject_var, width=18).pack(side=LEFT, padx=(0, 12))

        ttk.Label(controls, text="Class:").pack(side=LEFT, padx=(0, 4))
        self.class_var = tk.StringVar(value="CSE-A")
        ttk.Entry(controls, textvariable=self.class_var, width=10).pack(side=LEFT, padx=(0, 12))

        ttk.Button(controls, text="📂 Upload Photo", bootstyle="primary",
                   command=self._upload_and_process).pack(side=LEFT)

        # ── Image display ──────────────────────────────────────────────
        mid = ttk.Frame(self)
        mid.pack(fill=BOTH, expand=True, padx=24)

        img_panel = ttk.LabelFrame(mid, text="Classroom Image", width=640)
        img_panel.pack(side=LEFT, fill=Y, pady=8)
        img_panel.pack_propagate(False)

        self.img_label = ttk.Label(img_panel, text="No image loaded", anchor=CENTER)
        self.img_label.pack(fill=BOTH, expand=True, padx=8, pady=8)

        # ── Results panel ──────────────────────────────────────────────
        res_panel = ttk.Frame(mid)
        res_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=(16, 0), pady=8)

        # Stats bar
        self.stats_frame = ttk.Frame(res_panel)
        self.stats_frame.pack(fill=X, pady=(0, 12))
        self.stat_vars = {}
        for label, key, style in [
            ("Total", "total", "info"),
            ("Present", "present", "success"),
            ("Absent", "absent", "danger"),
            ("Unknown", "unknown", "warning"),
        ]:
            card = ttk.Frame(self.stats_frame, bootstyle=style, padding=10)
            card.pack(side=LEFT, padx=4, fill=X, expand=True)
            ttk.Label(card, text=label, font=("Segoe UI", 9), bootstyle=f"inverse-{style}").pack()
            var = tk.StringVar(value="—")
            ttk.Label(card, textvariable=var, font=("Segoe UI", 22, "bold"),
                      bootstyle=f"inverse-{style}").pack()
            self.stat_vars[key] = var

        # Present/Absent tables
        ttk.Label(res_panel, text="Present", font=("Segoe UI", 11, "bold"),
                  bootstyle="success").pack(anchor=W)
        self.present_tree = self._make_table(res_panel)
        self.present_tree.pack(fill=BOTH, expand=True, pady=(2, 8))

        ttk.Label(res_panel, text="Absent", font=("Segoe UI", 11, "bold"),
                  bootstyle="danger").pack(anchor=W)
        self.absent_tree = self._make_table(res_panel)
        self.absent_tree.pack(fill=BOTH, expand=True, pady=(2, 0))

    def _make_table(self, parent):
        cols = ("reg_no", "name", "confidence")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=7)
        tree.heading("reg_no",     text="Reg No")
        tree.heading("name",       text="Name")
        tree.heading("confidence", text="Match %")
        tree.column("reg_no",      width=100)
        tree.column("name",        width=180)
        tree.column("confidence",  width=80)
        return tree

    def _upload_and_process(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if not path:
            return
        subject = self.subject_var.get().strip()
        class_name = self.class_var.get().strip()
        if not subject or not class_name:
            messagebox.showerror("Error", "Please enter Subject and Class before processing.")
            return

        # Show spinner / disable button while processing
        self._set_processing_state(True)

        def run():
            try:
                result = take_attendance(path, subject, class_name)
                self.after(0, lambda: self._display_result(result))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.after(0, lambda: self._set_processing_state(False))

        threading.Thread(target=run, daemon=True).start()

    def _display_result(self, result: dict):
        self.result = result

        # Show annotated image
        img_bgr = result["annotated_img"]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(img_rgb)
        pil.thumbnail((620, 440))
        tk_img = ImageTk.PhotoImage(pil)
        self.img_label.configure(image=tk_img, text="")
        self.img_label.image = tk_img

        # Update stats
        self.stat_vars["total"].set(result["total_students"])
        self.stat_vars["present"].set(result["present_count"])
        self.stat_vars["absent"].set(result["absent_count"])
        self.stat_vars["unknown"].set(result["unknown_count"])

        # Populate tables
        self.present_tree.delete(*self.present_tree.get_children())
        for s in result["present"]:
            self.present_tree.insert("", END, values=(
                s["reg_no"], s["name"], f"{s['confidence']:.0%}"
            ))

        self.absent_tree.delete(*self.absent_tree.get_children())
        for s in result["absent"]:
            self.absent_tree.insert("", END, values=(s["reg_no"], s["name"], "—"))

    def _set_processing_state(self, processing: bool):
        # Could animate a spinner here; for MVP just update cursor
        self.configure(cursor="watch" if processing else "")
```

---

### 6.8 Reports Screen — `ui/ui_reports.py`

```python
# ui/ui_reports.py

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from ttkbootstrap.dialogs import Querybox
from services.attendance_service import get_report, export_report_excel
import pandas as pd
from datetime import date


class ReportsFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.df = None
        self._build()

    def on_show(self):
        self._load_report()

    def _build(self):
        # ── Filter bar ─────────────────────────────────────────────────
        bar = ttk.Frame(self)
        bar.pack(fill=X, padx=24, pady=16)

        ttk.Label(bar, text="Reports", font=("Segoe UI", 14, "bold")).pack(side=LEFT)

        fbar = ttk.Frame(bar)
        fbar.pack(side=RIGHT)

        ttk.Label(fbar, text="From:").pack(side=LEFT, padx=4)
        self.from_var = tk.StringVar(value="")
        ttk.Entry(fbar, textvariable=self.from_var, width=12).pack(side=LEFT)
        ttk.Label(fbar, text="To:").pack(side=LEFT, padx=(8, 4))
        self.to_var = tk.StringVar(value="")
        ttk.Entry(fbar, textvariable=self.to_var, width=12).pack(side=LEFT)
        ttk.Label(fbar, text="Subject:").pack(side=LEFT, padx=(8, 4))
        self.sub_var = tk.StringVar()
        ttk.Entry(fbar, textvariable=self.sub_var, width=14).pack(side=LEFT)

        ttk.Button(fbar, text="🔍 Filter", bootstyle="primary",
                   command=self._load_report).pack(side=LEFT, padx=8)
        ttk.Button(fbar, text="⬇ Export Excel", bootstyle="success-outline",
                   command=self._export).pack(side=LEFT)

        # ── Table ──────────────────────────────────────────────────────
        cols = ("date", "time", "subject", "class", "reg_no", "name", "status", "confidence")
        self.table = ttk.Treeview(self, columns=cols, show="headings", bootstyle="dark")
        headers = ("Date", "Time", "Subject", "Class", "Reg No", "Name", "Status", "Match %")
        widths  = (100,   80,    120,      80,     100,    180,    80,       80)
        for col, hdr, w in zip(cols, headers, widths):
            self.table.heading(col, text=hdr)
            self.table.column(col, width=w)

        self.table.tag_configure("present", foreground="#2ecc71")
        self.table.tag_configure("absent",  foreground="#e74c3c")

        scroll = ttk.Scrollbar(self, command=self.table.yview, bootstyle="round-dark")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side=LEFT, fill=BOTH, expand=True, padx=(24, 0), pady=(0, 24))
        scroll.pack(side=LEFT, fill=Y, pady=(0, 24), padx=(0, 8))

    def _load_report(self):
        try:
            self.df = get_report(
                from_date=self.from_var.get() or None,
                to_date=self.to_var.get() or None,
                subject=self.sub_var.get() or None,
            )
            self.table.delete(*self.table.get_children())
            for _, row in self.df.iterrows():
                tag = "present" if row["status"] == "present" else "absent"
                self.table.insert("", END, values=(
                    row["session_date"], row["session_time"], row["subject"],
                    row["class_name"], row["reg_no"], row["name"],
                    row["status"].upper(),
                    f"{row['confidence_pct']}%" if row["confidence_pct"] else "—"
                ), tags=(tag,))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _export(self):
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "Load a report first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if path:
            export_report_excel(self.df, path)
            messagebox.showinfo("Exported", f"Report saved to:\n{path}")
```

---

## 7. Environment Setup

### Step 1 — Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install all packages
pip install -r requirements.txt
```

**`requirements.txt`**

```txt
# AI / Vision
mediapipe==0.10.14
face-recognition==1.3.0         # Installs dlib automatically
opencv-python==4.9.0.80
numpy==1.26.4

# Database
mysql-connector-python==8.3.0
pandas==2.2.1
sqlalchemy==2.0.29              # Optional — for pd.read_sql

# UI
ttkbootstrap==1.10.1
Pillow==10.3.0

# Utilities
python-dotenv==1.0.1
openpyxl==3.1.2
scipy==1.13.0
```

> **Note on `face-recognition`:** On Windows, install CMake + Visual Studio Build Tools before pip installing. On Linux: `sudo apt install cmake libopenblas-dev liblapack-dev`. On Mac: `brew install cmake`.

---

### Step 2 — Configure `.env`

```env
# .env  — never commit this file
DB_HOST=localhost
DB_PORT=3306
DB_NAME=attendance_db
DB_USER=root
DB_PASSWORD=your_password_here

PHOTO_STORE=assets/student_photos
MATCH_THRESHOLD=0.5             # Lower = stricter matching (0.4 to 0.6 is typical)
```

---

### Step 3 — `config.py`

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "DB_HOST":         os.getenv("DB_HOST", "localhost"),
    "DB_PORT":         os.getenv("DB_PORT", "3306"),
    "DB_NAME":         os.getenv("DB_NAME", "attendance_db"),
    "DB_USER":         os.getenv("DB_USER", "root"),
    "DB_PASSWORD":     os.getenv("DB_PASSWORD", ""),
    "PHOTO_STORE":     os.getenv("PHOTO_STORE", "assets/student_photos"),
    "MATCH_THRESHOLD": os.getenv("MATCH_THRESHOLD", "0.5"),
}
```

---

### Step 4 — `main.py`

```python
# main.py
from ui.app import run

if __name__ == "__main__":
    run()
```

---

## 8. MySQL Bootstrap Script

```bash
# Run once to create DB and tables
mysql -u root -p < db/schema.sql

# Verify
mysql -u root -p attendance_db -e "SHOW TABLES;"
```

Expected output:
```
+-------------------------+
| Tables_in_attendance_db |
+-------------------------+
| attendance_records      |
| attendance_sessions     |
| face_encodings          |
| students                |
+-------------------------+
```

---

## 9. Configuration File

Summary of all tuneable parameters:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `MATCH_THRESHOLD` | `0.5` | Euclidean distance cutoff. **Lower** = more strict (fewer false positives, more false negatives). Recommended range: 0.4–0.55 |
| `min_detection_confidence` | `0.6` | MediaPipe confidence floor. Lower catches more faces but increases false detections |
| `num_jitters` in `face_encodings` | `2` (registration), `1` (attendance) | Higher = more accurate encoding but slower. Registration can afford 2; real-time attendance uses 1 |
| `max_dim` in `_preprocess` | `1280` | Max image dimension before resize. Keeps GPU/CPU load bounded |
| `pool_size` in MySQLConnectionPool | `5` | DB connections. Fine for single-machine MVP |

---

## 10. Accuracy & Tuning Notes

### Why Multiple Registration Photos?

A single photo can fail under different lighting, angles, or glasses. Registering 3–5 photos and averaging the encodings produces a more robust centroid in the 128-dim embedding space.

### CLAHE Pre-processing

Classroom photos often have uneven lighting (window light on one side). CLAHE (Contrast Limited Adaptive Histogram Equalization) normalises local contrast, improving detection and encoding quality without over-brightening.

### KDTree vs Linear Scan

For N ≤ 200 students, linear scan (NumPy dot products) is fast enough. KDTree gives O(log N) lookup and matters at N ≥ 500. This implementation uses KDTree from day one — no performance difference at small N, and zero refactor needed to scale.

### Threshold Selection

| Scenario | Recommended Threshold |
|----------|-----------------------|
| High-security (avoid proxy) | 0.40 |
| Balanced MVP | 0.50 |
| Diverse demographics, controlled lighting | 0.55 |
| Poor lighting, varied angles | 0.58 + CLAHE |

### Common Failure Modes & Fixes

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Student not detected | Face too small in frame, < 80px | Use a higher resolution image or move camera closer |
| Wrong student matched | Threshold too loose | Lower threshold to 0.45 |
| Registration fails — no face found | Poor photo quality | Use a front-facing, well-lit photo |
| Encoding mismatch after angle change | Only frontal photos registered | Add 3-quarter angle photos during registration |

---

## 11. Known Limitations & Future Scope

### Current MVP Limitations

- **Single image per session** — not continuous video
- **No liveness detection** — a printed photo of a student could fool the system
- **CPU-bound** — large class photos (40+ faces) take ~4–8 seconds to process
- **Local machine only** — no multi-room or networked deployment

### Phase 2 Roadmap (aligned with PPT Future Scope)

| Phase | Upgrade | Implementation Path |
|-------|---------|---------------------|
| **1** | Live webcam / CCTV stream | Replace single-image upload with `cv2.VideoCapture` loop; process every Nth frame |
| **2** | Liveness detection | Add MediaPipe FaceMesh eye-blink check or integrate Silent-Face-Anti-Spoofing model |
| **3** | Custom CNN for edge cases | Fine-tune ArcFace (InsightFace) on institutional dataset; replace dlib encodings |
| **4** | Cloud deployment | Flask REST API wrapper around service layer; deploy on AWS EC2; Tkinter → React frontend |
| **5** | Mobile app | FastAPI backend + Flutter app consuming same MySQL via REST |

### Replacing dlib in Phase 3

When upgrading to a custom CNN:

```python
# Drop-in replacement in face_engine.py
# Replace:   face_recognition.face_encodings(...)
# With:      insightface.app.FaceAnalysis().get(img)[i].embedding
# Everything else (KDTree, DB, Tkinter) stays identical.
```

---

*End of Implementation Blueprint*  
*Generated for: AI-Based Classroom Attendance System — U24AD401*
