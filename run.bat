@echo off
REM run.bat - Start the AI Attendance System

cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py
pause
