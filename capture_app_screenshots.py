import os
import sys
import ctypes
import ctypes.wintypes
from ctypes import windll, byref
from PIL import Image
import tkinter as tk
import ttkbootstrap as ttk

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', ctypes.c_uint32),
        ('biWidth', ctypes.c_int32),
        ('biHeight', ctypes.c_int32),
        ('biPlanes', ctypes.c_uint16),
        ('biBitCount', ctypes.c_uint16),
        ('biCompression', ctypes.c_uint32),
        ('biSizeImage', ctypes.c_uint32),
        ('biXPelsPerMeter', ctypes.c_int32),
        ('biYPelsPerMeter', ctypes.c_int32),
        ('biClrUsed', ctypes.c_uint32),
        ('biClrImportant', ctypes.c_uint32),
    ]

def capture_window_to_file(hwnd, filepath):
    user32 = windll.user32
    gdi32 = windll.gdi32

    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    hwndDC = user32.GetWindowDC(hwnd)
    memDC = gdi32.CreateCompatibleDC(hwndDC)
    saveBitMap = gdi32.CreateCompatibleBitmap(hwndDC, w, h)
    gdi32.SelectObject(memDC, saveBitMap)

    # PW_RENDERFULLCONTENT = 2
    res = user32.PrintWindow(hwnd, memDC, 2)
    if not res:
        res = user32.PrintWindow(hwnd, memDC, 0)

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = w
    bmi.biHeight = -h  # top-down DIB
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buf = (ctypes.c_char * (w * h * 4))()
    gdi32.GetDIBits(memDC, saveBitMap, 0, h, buf, ctypes.byref(bmi), 0)

    img = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1)
    rgb_img = img.convert('RGB')
    rgb_img.save(filepath)
    print(f"[SUCCESS] Saved screenshot to {filepath} (Size: {w}x{h})")

    gdi32.DeleteObject(saveBitMap)
    gdi32.DeleteDC(memDC)
    user32.ReleaseDC(hwnd, hwndDC)

def run_capture():
    from ui.app import AttendanceApp
    from services.attendance_service import take_attendance, initialise_engine
    
    # 1. Initialize engine
    initialise_engine()
    
    # 2. Launch App
    app = AttendanceApp()
    app.geometry("1180x740")
    app.update()

    # 3. Process Attendance Screen
    att_frame = app._frames["attendance"]
    att_frame.subject_var.set("Mathematics")
    att_frame.class_var.set("CSE-A")

    # Run attendance on demo image
    res = take_attendance("assets/test_classroom_session.jpg", "Mathematics", "CSE-A")
    att_frame._display_result(res)
    app.update_idletasks()
    app.update()

    hwnd = app.winfo_id()
    # Capture Frame 1: Attendance Processing Screen
    capture_window_to_file(hwnd, "screenshot_attendance_window.png")

    # 4. Switch to Reports Screen
    app._show_frame("reports")
    rep_frame = app._frames["reports"]
    rep_frame._load_report()
    app.update_idletasks()
    app.update()

    # Capture Frame 2: Attendance Reports & Analytics Screen
    capture_window_to_file(hwnd, "screenshot_reports_window.png")

    app.destroy()
    print("[ALL DONE] Captured both screenshots successfully!")

if __name__ == "__main__":
    run_capture()
