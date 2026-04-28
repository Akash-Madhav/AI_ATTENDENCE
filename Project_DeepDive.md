# AI Attendance System: Deep-Dive Workflow & Architecture

This document provides a comprehensive technical breakdown of the **AI Attendance System**, focusing on the professional-grade vision pipeline, the database-driven workflow, and the mathematical logic behind face matching.

---

## 1. Vision Pipeline: The SFace + YuNet Engine

The system uses a high-performance, industry-standard face recognition pipeline based on the **YuNet** and **SFace** models, integrated via OpenCV's `dnn` module.

### Stage 1: Face Detection (YuNet)
- **Model**: `face_detection_yunet_2023mar.onnx`
- **Architecture**: A lightweight CNN optimized for edge devices and real-time performance.
- **Capability**: It detects face bounding boxes and **5 facial landmarks** (eyes, nose, and mouth corners).
- **Why YuNet?**: Unlike Haar Cascades (legacy) or MediaPipe (CPU-heavy), YuNet is specifically designed to handle extreme angles, low lighting, and occlusions (like masks or glasses) while maintaining high speed on group photos.

### Stage 2: Face Alignment & Recognition (SFace)
- **Model**: `face_recognition_sface_2021dec.onnx`
- **Capability**: 
    1.  **Alignment**: Uses the landmarks from YuNet to warp and crop the face into a standard orientation (frontal view).
    2.  **Feature Extraction**: Processes the aligned face to generate a **128-dimensional vector (embedding)**.
- **Normalization**: The feature vector is normalized to unit length. This transforms the high-dimensional space such that the **Euclidean Distance** between two vectors becomes mathematically equivalent to their **Cosine Similarity**.

---

## 2. System Workflow

### A. Student Registration (Training)
1.  **Input**: User uploads multiple photos of a student.
2.  **Detection**: YuNet identifies the face and landmarks in each photo.
3.  **Encoding**: SFace generates a 128-dim vector for each face.
4.  **Averaging**: The system calculates the mean vector from all photos to create a "Golden Embedding" that captures the student's unique features across different angles.
5.  **Storage**: 
    - Student details (Name, Reg No) are stored in the `students` table.
    - The Golden Embedding is pickled and stored as a `BLOB` in the `face_encodings` table.

### B. Attendance Taking (Inference)
1.  **Input**: Teacher uploads a classroom photo containing multiple students.
2.  **Detection**: YuNet scans the entire image and detects *all* faces.
3.  **Encoding**: Each detected face is aligned and encoded into a 128-dim vector.
4.  **Vector Matching (KDTree)**:
    - At startup, the system loads all student embeddings from the database into a **SciPy KDTree**.
    - For each face in the classroom photo, the system performs a "Nearest Neighbor" search in the KDTree.
5.  **Classification**:
    - If `distance < MATCH_THRESHOLD` (default 0.8), the face is marked as **Present** with a calculated confidence score.
    - If `distance >= MATCH_THRESHOLD`, the face is marked as **Unknown**.
6.  **Persistence**: 
    - A new `attendance_session` is created.
    - `attendance_records` are generated for *every* student (status='present' or 'absent').

---

## 3. Mathematical Logic: Match Confidence

The system converts the raw distance from the KDTree into a human-readable confidence percentage.

### The Formula
Since vectors are normalized to unit length, the relationship between Euclidean Distance ($d$) and Cosine Similarity ($s$) is:
$$s = 1 - \frac{d^2}{2}$$

- **Match**: A similarity of 1.0 is a perfect match. 
- **Threshold**: We use a distance threshold (typically 0.8). If the distance is smaller, the similarity is high enough to confirm identity.

---

## 4. Database Schema Relationships

The MySQL database ensures data integrity and prevents duplicate attendance for the same student in a single session.

- **`students`**: Master list of registered students.
- **`face_encodings`**: Stores the 128-dim vectors linked to `student_id`.
- **`attendance_sessions`**: Metadata for a specific class (subject, date, time, image path).
- **`attendance_records`**: The bridge table linking students to sessions.
    - Uses a `UNIQUE(session_id, student_id)` constraint to prevent double-marking.
    - Automatically calculates **Absentees** by comparing the set of "Present" students against the master `students` table.

---

## 5. Technology Stack Summary

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Vision Engine** | OpenCV + DNN | YuNet (Detector) & SFace (Recognizer) |
| **Math/Search** | SciPy + NumPy | KDTree for $O(\log N)$ fast vector matching |
| **Database** | MySQL | Persistent storage for students and attendance |
| **UI** | Tkinter + ttkbootstrap | Modern, dark-themed desktop dashboard |
| **Reporting** | Pandas + OpenPyxl | Excel generation and data analysis |

---

> [!TIP]
> **Performance Tip**: The KDTree allows the system to match a face against thousands of registered students in milliseconds, making it scalable for large institutions.
