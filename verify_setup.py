"""Verify setup script for AI Attendance System.
Checks Python dependencies, model files, photo store, and MySQL DB connection.
"""

import os
import sys

# Ensure UTF-8 output encoding for Windows terminal compatibility
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def verify():
    print("========================================")
    print(" AI Attendance System - Setup Verification")
    print("========================================")

    all_passed = True

    # 1. Verify Dependencies
    print("\n[1/4] Checking Python Packages...")
    required_packages = [
        ("cv2", "OpenCV"),
        ("numpy", "NumPy"),
        ("mysql.connector", "MySQL Connector"),
        ("pandas", "Pandas"),
        ("sqlalchemy", "SQLAlchemy"),
        ("ttkbootstrap", "TTKBootstrap"),
        ("scipy", "SciPy"),
        ("dotenv", "Python-Dotenv")
    ]
    for mod_name, label in required_packages:
        try:
            __import__(mod_name)
            print(f"  [OK] {label} ({mod_name}) is installed")
        except ImportError:
            print(f"  [FAIL] {label} ({mod_name}) is NOT installed")
            all_passed = False

    # 2. Verify Models
    print("\n[2/4] Checking AI Models...")
    models_dir = os.path.join(os.path.dirname(__file__), "assets", "models")
    yunet_path = os.path.join(models_dir, "face_detection_yunet_2023mar.onnx")
    sface_path = os.path.join(models_dir, "face_recognition_sface_2021dec.onnx")

    if os.path.exists(yunet_path):
        print(f"  [OK] YuNet Detector model found: {os.path.basename(yunet_path)}")
    else:
        print(f"  [FAIL] YuNet Detector model missing: {yunet_path}")
        all_passed = False

    if os.path.exists(sface_path):
        print(f"  [OK] SFace Recognizer model found: {os.path.basename(sface_path)}")
    else:
        print(f"  [FAIL] SFace Recognizer model missing: {sface_path}")
        all_passed = False

    # 3. Verify Photo Store Directory
    print("\n[3/4] Checking Photo Store Directory...")
    from config import CONFIG
    photo_store = CONFIG.get("PHOTO_STORE", "assets/student_photos")
    if not os.path.isabs(photo_store):
        photo_store = os.path.join(os.path.dirname(__file__), photo_store)
    
    os.makedirs(photo_store, exist_ok=True)
    print(f"  [OK] Photo store directory ready: {photo_store}")

    # 4. Verify Database Connection
    print("\n[4/4] Checking Database Connection...")
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=CONFIG["DB_HOST"],
            port=CONFIG["DB_PORT"],
            user=CONFIG["DB_USER"],
            password=CONFIG["DB_PASSWORD"],
            database=CONFIG["DB_NAME"]
        )
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [t[0] for t in cursor.fetchall()]
        cursor.close()
        conn.close()
        print(f"  [OK] Database '{CONFIG['DB_NAME']}' connected successfully!")
        print(f"       Tables found: {', '.join(tables) if tables else 'None (run python setup_database.py)'}")
        if not tables:
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Database connection failed: {e}")
        print("         Please ensure MySQL is running and .env has valid DB credentials.")
        all_passed = False

    print("\n========================================")
    if all_passed:
        print(" SUCCESS: All setup checks passed successfully!")
        print(" You can now run the app with: python main.py")
    else:
        print(" WARNING: Some setup checks failed. Please fix the issues above.")
    print("========================================")

if __name__ == "__main__":
    verify()
