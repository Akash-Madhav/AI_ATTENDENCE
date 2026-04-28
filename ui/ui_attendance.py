# ui/ui_attendance.py

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import threading
from services.attendance_service import take_attendance


class AttendanceFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.result = None
        self._build()

    def _build(self):
        # ── Top controls ───────────────────────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill=X, padx=24, pady=16)

        ttk.Label(top, text="Take Attendance", font=("Segoe UI", 14, "bold")).pack(side=LEFT)

        controls = ttk.Frame(top)
        controls.pack(side=RIGHT)

        ttk.Label(controls, text="Subject:").pack(side=LEFT, padx=(0, 4))
        self.subject_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=self.subject_var, width=18).pack(side=LEFT, padx=(0, 12))

        ttk.Label(controls, text="Class:").pack(side=LEFT, padx=(0, 4))
        self.class_var = tk.StringVar(value="CSE-A")
        ttk.Entry(controls, textvariable=self.class_var, width=10).pack(side=LEFT, padx=(0, 12))

        ttk.Button(controls, text="📂 Upload Photo", bootstyle="primary",
                   command=self._upload_and_process).pack(side=LEFT)

        # ── Image display ──────────────────────────────────────────────
        mid = ttk.Frame(self)
        mid.pack(fill=BOTH, expand=True, padx=24)

        img_panel = ttk.LabelFrame(mid, text="Classroom Image", width=640)
        img_panel.pack(side=LEFT, fill=Y, pady=8)
        img_panel.pack_propagate(False)

        self.img_label = ttk.Label(img_panel, text="No image loaded", anchor=CENTER)
        self.img_label.pack(fill=BOTH, expand=True, padx=8, pady=8)

        # ── Results panel ──────────────────────────────────────────────
        res_panel = ttk.Frame(mid)
        res_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=(16, 0), pady=8)

        # Stats bar
        self.stats_frame = ttk.Frame(res_panel)
        self.stats_frame.pack(fill=X, pady=(0, 12))
        self.stat_vars = {}
        for label, key, style in [
            ("Total", "total", "info"),
            ("Present", "present", "success"),
            ("Absent", "absent", "danger"),
            ("Unknown", "unknown", "warning"),
        ]:
            card = ttk.Frame(self.stats_frame, bootstyle=style, padding=10)
            card.pack(side=LEFT, padx=4, fill=X, expand=True)
            ttk.Label(card, text=label, font=("Segoe UI", 9), bootstyle=f"inverse-{style}").pack()
            var = tk.StringVar(value="—")
            ttk.Label(card, textvariable=var, font=("Segoe UI", 22, "bold"),
                      bootstyle=f"inverse-{style}").pack()
            self.stat_vars[key] = var

        # Present/Absent tables
        ttk.Label(res_panel, text="Present", font=("Segoe UI", 11, "bold"),
                  bootstyle="success").pack(anchor=W)
        self.present_tree = self._make_table(res_panel)
        self.present_tree.pack(fill=BOTH, expand=True, pady=(2, 8))

        ttk.Label(res_panel, text="Absent", font=("Segoe UI", 11, "bold"),
                  bootstyle="danger").pack(anchor=W)
        self.absent_tree = self._make_table(res_panel)
        self.absent_tree.pack(fill=BOTH, expand=True, pady=(2, 0))

    def _make_table(self, parent):
        cols = ("reg_no", "name", "confidence")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=7)
        tree.heading("reg_no",     text="Reg No")
        tree.heading("name",       text="Name")
        tree.heading("confidence", text="Match %")
        tree.column("reg_no",      width=100)
        tree.column("name",        width=180)
        tree.column("confidence",  width=80)
        return tree

    def _upload_and_process(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if not path:
            return
        subject = self.subject_var.get().strip()
        class_name = self.class_var.get().strip()
        if not subject or not class_name:
            messagebox.showerror("Error", "Please enter Subject and Class before processing.")
            return

        # Show spinner / disable button while processing
        self._set_processing_state(True)

        def run():
            try:
                result = take_attendance(path, subject, class_name)
                self.after(0, lambda: self._display_result(result))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.after(0, lambda: self._set_processing_state(False))

        threading.Thread(target=run, daemon=True).start()

    def _display_result(self, result: dict):
        self.result = result

        # Show annotated image
        img_bgr = result["annotated_img"]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(img_rgb)
        pil.thumbnail((620, 440))
        tk_img = ImageTk.PhotoImage(pil)
        self.img_label.configure(image=tk_img, text="")
        self.img_label.image = tk_img

        # Update stats
        self.stat_vars["total"].set(result["total_students"])
        self.stat_vars["present"].set(result["present_count"])
        self.stat_vars["absent"].set(result["absent_count"])
        self.stat_vars["unknown"].set(result["unknown_count"])

        # Populate tables
        self.present_tree.delete(*self.present_tree.get_children())
        for s in result["present"]:
            self.present_tree.insert("", END, values=(
                s["reg_no"], s["name"], f"{s['confidence']:.0%}"
            ))

        self.absent_tree.delete(*self.absent_tree.get_children())
        for s in result["absent"]:
            self.absent_tree.insert("", END, values=(s["reg_no"], s["name"], "—"))

    def _set_processing_state(self, processing: bool):
        self.configure(cursor="watch" if processing else "")
