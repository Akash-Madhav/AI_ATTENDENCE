# ui/ui_reports.py

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from services.attendance_service import get_report, export_report_excel
import pandas as pd


class ReportsFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.df = None
        self._build()

    def on_show(self):
        self._load_report()

    def _build(self):
        # ── Filter bar ─────────────────────────────────────────────────
        bar = ttk.Frame(self)
        bar.pack(fill=X, padx=24, pady=16)

        ttk.Label(bar, text="Reports", font=("Segoe UI", 14, "bold")).pack(side=LEFT)

        fbar = ttk.Frame(bar)
        fbar.pack(side=RIGHT)

        ttk.Label(fbar, text="From:").pack(side=LEFT, padx=4)
        self.from_var = tk.StringVar(value="")
        ttk.Entry(fbar, textvariable=self.from_var, width=12).pack(side=LEFT)
        ttk.Label(fbar, text="To:").pack(side=LEFT, padx=(8, 4))
        self.to_var = tk.StringVar(value="")
        ttk.Entry(fbar, textvariable=self.to_var, width=12).pack(side=LEFT)
        ttk.Label(fbar, text="Subject:").pack(side=LEFT, padx=(8, 4))
        self.sub_var = tk.StringVar()
        ttk.Entry(fbar, textvariable=self.sub_var, width=14).pack(side=LEFT)

        ttk.Button(fbar, text="🔍 Filter", bootstyle="primary",
                   command=self._load_report).pack(side=LEFT, padx=8)
        ttk.Button(fbar, text="⬇ Export Excel", bootstyle="success-outline",
                   command=self._export).pack(side=LEFT)

        # ── Table ──────────────────────────────────────────────────────
        cols = ("date", "time", "subject", "class", "reg_no", "name", "status", "confidence")
        self.table = ttk.Treeview(self, columns=cols, show="headings", bootstyle="dark")
        headers = ("Date", "Time", "Subject", "Class", "Reg No", "Name", "Status", "Match %")
        widths  = (100,   80,    120,      80,     100,    180,    80,       80)
        for col, hdr, w in zip(cols, headers, widths):
            self.table.heading(col, text=hdr)
            self.table.column(col, width=w)

        self.table.tag_configure("present", foreground="#2ecc71")
        self.table.tag_configure("absent",  foreground="#e74c3c")

        scroll = ttk.Scrollbar(self, command=self.table.yview, bootstyle="round-dark")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side=LEFT, fill=BOTH, expand=True, padx=(24, 0), pady=(0, 24))
        scroll.pack(side=LEFT, fill=Y, pady=(0, 24), padx=(0, 8))

    def _load_report(self):
        try:
            self.df = get_report(
                from_date=self.from_var.get() or None,
                to_date=self.to_var.get() or None,
                subject=self.sub_var.get() or None,
            )
            self.table.delete(*self.table.get_children())
            for _, row in self.df.iterrows():
                tag = "present" if row["status"] == "present" else "absent"
                self.table.insert("", END, values=(
                    row["session_date"], row["session_time"], row["subject"],
                    row["class_name"], row["reg_no"], row["name"],
                    row["status"].upper(),
                    f"{row['confidence_pct']}%" if row["confidence_pct"] else "—"
                ), tags=(tag,))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _export(self):
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "Load a report first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if path:
            export_report_excel(self.df, path)
            messagebox.showinfo("Exported", f"Report saved to:\n{path}")
