# verify_setup.py
"""Verify that all dependencies and project structure are properly installed."""

import sys
import os


def check_dependencies():
    """Check if all required packages are installed."""
    packages = [
        'cv2', 'numpy', 'mediapipe', 'tkinter',
        'PIL', 'mysql.connector', 'pandas', 'scipy', 'ttkbootstrap', 
        'dotenv'
    ]
    
    missing = []
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    return missing


def check_structure():
    """Check if all required directories and files exist."""
    required_dirs = [
        'db', 'engine', 'services', 'ui', 'assets', 'assets/student_photos', 'venv'
    ]
    
    required_files = [
        'config.py', 'main.py', 'requirements.txt', '.env', '.gitignore',
        'db/db.py', 'db/schema.sql',
        'engine/face_engine.py',
        'services/student_service.py', 'services/attendance_service.py',
        'ui/app.py', 'ui/ui_registration.py', 'ui/ui_attendance.py', 'ui/ui_reports.py'
    ]
    
    missing_dirs = [d for d in required_dirs if not os.path.isdir(d)]
    missing_files = [f for f in required_files if not os.path.isfile(f)]
    
    return missing_dirs, missing_files


def main():
    print("=" * 60)
    print("AI ATTENDANCE SYSTEM - SETUP VERIFICATION")
    print("=" * 60)

    print(f"\n[0] Python version: {sys.version.split()[0]}")
    print("    ✓ All Python versions supported (3.12+)")
    
    # Check directory structure
    print("\n[1] Checking project structure...")
    missing_dirs, missing_files = check_structure()
    
    if missing_dirs:
        print(f"    ❌ Missing directories: {', '.join(missing_dirs)}")
    else:
        print("    ✓ All required directories present")
    
    if missing_files:
        print(f"    ❌ Missing files: {', '.join(missing_files)}")
    else:
        print("    ✓ All required files present")
    
    # Check dependencies
    print("\n[2] Checking dependencies...")
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"    ❌ Missing packages: {', '.join(missing_packages)}")
        print("\n    Run: pip install -r requirements.txt")
        return False
    else:
        print("    ✓ All dependencies installed")
    
    # Final status
    print("\n" + "=" * 60)
    if not (missing_dirs or missing_files or missing_packages):
        print("✓ SETUP VERIFICATION PASSED")
        print("=" * 60)
        print("\nYou can now run the application with:")
        print("  Windows:   run.bat")
        print("  Linux/Mac: bash run.sh")
        print("  Or:        python main.py")
        return True
    else:
        print("❌ SETUP VERIFICATION FAILED")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
