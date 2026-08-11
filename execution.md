# Execution Guide & Model Architecture

This document explains how to set up, verify, and run the **AI Attendance System** on Windows, as well as the deep-learning models powering the facial recognition engine.

---

## Quick Start (Python 3.12 / 3.13 / 3.14)

```powershell
cd C:\Users\akash\AI_ATTENDENCE
py -m venv venv
.\venv\Scripts\activate
python --version
pip install -r requirements.txt
python setup_database.py
python verify_setup.py
```

If setup verification passes:

```powershell
python main.py
```

---

## 1. Prerequisites

- **Python**: 3.12, 3.13, or 3.14 (64-bit recommended)
- **Database**: MySQL 8.x running locally (Service name typically `MySQL80` or `MySQL`)
- **Shell**: PowerShell or Command Prompt

---

## 2. Setup & Execution Steps

### Step 1: Open Project Folder
```powershell
cd C:\Users\akash\AI_ATTENDENCE
```

### Step 2: Create & Activate Virtual Environment
```powershell
py -m venv venv
.\venv\Scripts\activate
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```
*(Or run `.\install_packages.bat`)*

### Step 4: Configure Database & Environment
Ensure `.env` exists in the root directory with correct MySQL credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=attendance_db
DB_USER=root
DB_PASSWORD=your_mysql_password
PHOTO_STORE=assets/student_photos
MATCH_THRESHOLD=0.8
```

### Step 5: Initialize Database Schema
```powershell
python setup_database.py
```
This reads `db/schema.sql` and creates `attendance_db` along with all required tables (`students`, `attendance_sessions`, `attendance_records`).

### Step 6: Verify Setup
```powershell
python verify_setup.py
```
This script checks:
1. Python dependencies (`opencv-python`, `numpy`, `mysql-connector-python`, `pandas`, `sqlalchemy`, `ttkbootstrap`, `scipy`, `python-dotenv`).
2. AI Model files availability (`assets/models/`).
3. Photo store directory readiness (`assets/student_photos/`).
4. Active MySQL connection and database schema verification.

### Step 7: Launch Application
Option A (PowerShell / CMD):
```powershell
python main.py
```

Option B (Batch launcher):
```powershell
.\run.bat
```

---

## 3. The 2 AI Models & Their Purpose

The AI Attendance System operates on a **2-Stage Deep Learning Pipeline** using OpenCV ONNX models.

| Model File | Model Name | Role / Purpose |
| :--- | :--- | :--- |
| `face_detection_yunet_2023mar.onnx` | **YuNet** | **Stage 1: Deep Learning Face Detection & Landmark Extraction** |
| `face_recognition_sface_2021dec.onnx` | **SFace** | **Stage 2: Facial Alignment & 128-Dim Feature Vector Extraction** |

---

### Model 1: YuNet Detector (`face_detection_yunet_2023mar.onnx`)

- **Architecture**: Lightweight, real-time Convolutional Neural Network (CNN) face detector.
- **Model File**: `assets/models/face_detection_yunet_2023mar.onnx` (approx. 232 KB)
- **Primary Purpose**: 
  - Detects all human faces in a camera feed or classroom image, regardless of scale, lighting, or minor rotation.
  - Computes exact **bounding boxes** `(x, y, w, h)` for each detected face.
  - Extracts **5 key facial landmarks**:
    1. Right Eye center
    2. Left Eye center
    3. Nose tip
    4. Right Mouth corner
    5. Left Mouth corner

- **Why It Is Used**: YuNet is extremely fast, highly accurate, and designed specifically to detect multiple crowded faces simultaneously (ideal for classroom attendance photos) while outputting spatial landmarks needed for facial alignment.

---

### Model 2: SFace Recognizer (`face_recognition_sface_2021dec.onnx`)

- **Architecture**: Deep Neural Network trained for facial recognition and metric learning.
- **Model File**: `assets/models/face_recognition_sface_2021dec.onnx` (approx. 38.6 MB)
- **Primary Purpose**:
  1. **Facial Alignment (`alignCrop`)**: Uses the 5 landmarks output by YuNet to crop, rotate, scale, and align the detected face into a standardized 112x112 pixel normalized view.
  2. **Embedding Extraction (`feature`)**: Converts the aligned face image into a compact **128-dimensional feature embedding vector**.
  3. **Unit Normalization**: Normalizes the feature vector so that Euclidean distance corresponds directly to Cosine Similarity.

- **Why It Is Used**: SFace generates invariant facial embeddings that represent unique human facial features. This allows comparing faces across different photos regardless of head posture, expressions, or minor lighting variations.

---

### How The 2 Models Work Together in Code (`engine/face_engine.py`)

```
   [ Input Image (Classroom / Student Photo) ]
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │  Model 1: YuNet (Face Detector)     │
    └─────────────────────────────────────┘
                       │
     Bounding Boxes + 5 Facial Landmarks
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │  Model 2: SFace (Recognizer)        │
    │  1. Landmark-based Face Alignment   │
    │  2. 128-dim Feature Vector Extraction│
    └─────────────────────────────────────┘
                       │
         128-dim Normalized Feature Vector
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │  SciPy KDTree Matcher (Vector Index)│
    │  Cosine Similarity Distance Query   │
    └─────────────────────────────────────┘
                       │
                       ▼
       [ Identified Student ID & Attendance ]
```

1. **Detection**: `YuNet` scans the classroom image and finds face bounding boxes along with 5 facial landmarks.
2. **Alignment & Feature Extraction**: For every detected face, `SFace` aligns the cropped image using the 5 landmarks and extracts a 128-dimensional numerical representation of the face.
3. **Database Comparison**: The extracted 128-dim vector is queried against registered student face vectors stored in memory via a `SciPy KDTree` index using Cosine Similarity (`distance < MATCH_THRESHOLD`).
4. **Attendance Logging**: Matched student IDs are flagged as `Present` with a confidence score (`1.0 - distance`), while unmatched faces are marked as `Unknown`.

---

## 4. First-Time Usage Workflow

1. **Student Registration**:
   - Go to **Register Student** tab in the UI.
   - Enter Student Name, Roll Number, Department, and Semester.
   - Upload 1 to 5 reference photos. The system processes them through **YuNet + SFace** and saves the averaged 128-dim vector into the MySQL database.
2. **Take Attendance**:
   - Go to **Take Attendance** tab.
   - Select Course, Date, and Upload/Capture a classroom image.
   - Click **Process Attendance**. YuNet and SFace detect all students in the photo and compare them against registered embeddings.
3. **View & Export Reports**:
   - Go to **Reports** tab to review attendance records and export data to CSV/Excel formats.

---

## 5. Troubleshooting & FAQs

### Q1: Face Not Recognized?
- Check if student reference photos in `assets/student_photos` are clear and front-facing.
- Adjust `MATCH_THRESHOLD` in `.env` (default is `0.8`). Lowering threshold makes matching stricter, raising it allows more relaxed matching.

### Q2: MySQL Access Denied?
- Make sure MySQL 8.x service is running: `net start MySQL80`
- Update `.env` with your actual MySQL password (`DB_PASSWORD=...`).
- Run `python setup_database.py` again.

---

## 6. Daily Startup Command

```powershell
cd C:\Users\akash\AI_ATTENDENCE
.\run.bat
```
