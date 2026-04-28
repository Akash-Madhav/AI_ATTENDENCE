# README.md

# AI-Based Classroom Attendance System

Desktop MVP for face recognition-based attendance tracking using Python, MediaPipe, and MySQL.

## Quick Start

### 1. Setup Virtual Environment

```bash
# Create venv (Python 3.14, 3.13, or 3.12)
py -m venv venv

# Activate venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Database

Edit `.env` with your MySQL credentials:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=attendance_db
```

Run schema script:
```bash
mysql -u root -p < db/schema.sql
```

### 3. Run Application

```bash
python main.py
```

## Project Structure

```
attendance-system/
├── venv/                    # Virtual environment
├── db/                      # Database layer
├── engine/                  # Face recognition engine
├── services/                # Business logic
├── ui/                      # Tkinter UI
├── assets/                  # Student photos
├── config.py                # Configuration loader
├── main.py                  # Entry point
└── requirements.txt         # Dependencies
```

## Features

- **Student Registration**: Register students with multiple reference photos
- **Face Detection**: OpenCV Haar Cascade (fully compatible with all Python versions)
- **Face Encoding**: Normalized face crop encoding using OpenCV (Python 3.14 compatible)
- **Attendance Taking**: Upload classroom photo for automatic attendance
- **Reports**: Generate and export attendance reports to Excel

## Requirements

- Python 3.12, 3.13, or 3.14 (any version supported)
- MySQL 8.0+
- Windows/macOS/Linux

## Python Version Compatibility

As of this version, the project uses OpenCV for face encoding instead of dlib, making it fully compatible with **Python 3.14**.
No C++ build tools or special setup required — just install the dependencies normally.

## Tech Stack

- **Vision**: OpenCV
- **Database**: MySQL, pandas
- **UI**: Tkinter, ttkbootstrap
- **Utilities**: numpy, scipy, python-dotenv

## Configuration

Tunable parameters in `.env`:
- `MATCH_THRESHOLD`: Face distance threshold (default: 0.6, range: 0.5-0.7)
- `PHOTO_STORE`: Directory for student reference photos
