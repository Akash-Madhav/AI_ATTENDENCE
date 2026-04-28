# Execution Guide

This document explains how to set up and run the AI Attendance System on Windows.

## Quick Start (Python 3.14 Compatible)

```powershell
cd C:\Users\akash\AI_ATTENDENCE
py -m venv venv
.\venv\Scripts\activate
python --version
pip install -r requirements.txt
python setup_database.py
venv\Scripts\python verify_setup.py
```

If successful, then:

```powershell
python main.py
```

## 1. Prerequisites

- Python 3.12, 3.13, or 3.14
- MySQL 8.x running locally
- PowerShell or Command Prompt

## 2. Open Project Folder

```powershell
cd C:\Users\akash\AI_ATTENDENCE
```

## 3. Create Virtual Environment

```powershell
py -m venv venv
```

Activate:

```powershell
.\venv\Scripts\activate
```

Verify version:

```powershell
python --version
```

Expected: `Python 3.12.x`, `3.13.x`, or `3.14.x`

## 4. Install Dependencies

Preferred:

```powershell
pip install -r requirements.txt
```

Or use the installer script:

```powershell
.\install_packages.bat
```

## 5. Configure Environment

Edit `.env` and set DB credentials:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=attendance_db
DB_USER=root
DB_PASSWORD=your_password
PHOTO_STORE=assets/student_photos
MATCH_THRESHOLD=0.5
```

## 6. Initialize Database

Run setup script:

```powershell
python setup_database.py
```

This reads `db/schema.sql` and creates the database and tables via Python (works on all systems).

## 7. Verify Setup

```powershell
venv\Scripts\python verify_setup.py
```

If successful, it should report setup passed.

## 8. Run Application

Option A:

```powershell
.\run.bat
```

Option B:

```powershell
python main.py
```

## 9. First Usage Flow

1. Open Register Student screen.
2. Add student details and 1 to 5 photos.
3. Open Take Attendance screen.
4. Upload class image and process attendance.
5. Open Reports screen to view/export report.

## 10. Face Recognition Upgrade (v3.0-SFace)

The system now uses a professional deep-learning pipeline:
- **Detection**: YuNet CNN (extracts 5 facial landmarks).
- **Alignment**: SFace automatically aligns/rotates faces based on landmarks.
- **Recognition**: SFace 128-dim embeddings for industry-standard accuracy.

The engine status is logged to the terminal on startup. Look for:
`[INFO] FaceEngine Version: 3.0-SFace`
`[SUCCESS] YuNet Detector loaded.`
`[SUCCESS] SFace Recognizer loaded.`

## 11. Common Issues

### A) Face not recognized
- Ensure the student photo in `assets/student_photos` is clear.
- Increase `MATCH_THRESHOLD` in `.env` if matching is too strict (default 0.8).

### B) MySQL connection error
- Check: MySQL service is running: `net start MySQL80`
- Check: `.env` credentials are correct.

## 12. Daily Run Commands

```powershell
cd C:\Users\akash\AI_ATTENDENCE
.\run.bat
```
