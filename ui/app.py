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
        super().__init__(themename="darkly")
        self.title("AI Attendance System")
        self.geometry("1200x750")
        self.minsize(900, 600)
        self.resizable(True, True)

        # Load face encodings into KDTree at startup
        try:
            initialise_engine()
        except Exception as e:
            print(f"Warning: Could not initialise engine: {e}")

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
