@echo off
setlocal
REM install_packages.bat - Install project dependencies in venv

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
	echo [ERROR] Virtual environment not found.
	echo Create it first: python -m venv venv
	pause
	exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo ========================================
echo Installing Packages
echo ========================================
echo.

echo [1] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
	echo [ERROR] Failed to upgrade pip.
	pause
	exit /b 1
)

echo [2] Installing packages from requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
	echo [ERROR] Installation failed.
	echo Check your internet connection and try again.
	pause
	exit /b 1
)

echo [3] Verifying installation...
venv\Scripts\python verify_setup.py

echo.
echo ========================================
echo Installation Complete
echo ========================================
echo.
echo Next: Configure .env and run: run.bat
echo.
pause
