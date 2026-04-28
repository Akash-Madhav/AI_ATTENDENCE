# ui/ui_registration.py

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from services.student_service import register_student, get_all_students, delete_student
import os


class RegistrationFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.photo_paths = []
        self.photo_labels = []
        self._build()

    def on_show(self):
        self._refresh_table()

    def _build(self):
        # ── Left panel: form ───────────────────────────────────────────
        left = ttk.Frame(self, width=380)
        left.pack(side=LEFT, fill=Y, padx=24, pady=24)
        left.pack_propagate(False)

        ttk.Label(left, text="Register New Student", font=("Segoe UI", 14, "bold")).pack(anchor=W, pady=(0, 16))

        # Form fields
        fields = [("Full Name", "name"), ("Reg Number", "reg_no"), ("Department", "dept")]
        self.vars = {}
        for label, key in fields:
            ttk.Label(left, text=label).pack(anchor=W, pady=(8, 2))
            var = tk.StringVar()
            ttk.Entry(left, textvariable=var, width=36).pack(anchor=W)
            self.vars[key] = var

        # Photo picker
        ttk.Label(left, text="Reference Photos (1–5)").pack(anchor=W, pady=(16, 4))
        self.photo_strip = ttk.Frame(left)
        self.photo_strip.pack(anchor=W)

        ttk.Button(left, text="+ Add Photos", bootstyle="secondary",
                   command=self._pick_photos).pack(anchor=W, pady=8)

        ttk.Button(left, text="Register Student", bootstyle="success",
                   command=self._submit, width=30).pack(pady=(16, 0))

        # ── Right panel: student table ─────────────────────────────────
        right = ttk.Frame(self)
        right.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 24), pady=24)

        ttk.Label(right, text="Registered Students", font=("Segoe UI", 14, "bold")).pack(anchor=W, pady=(0, 12))

        cols = ("reg_no", "name", "department", "registered")
        self.table = ttk.Treeview(right, columns=cols, show="headings", height=18, bootstyle="dark")
        for col, heading, width in zip(cols, ("Reg No", "Name", "Department", "Date"), (120, 200, 160, 120)):
            self.table.heading(col, text=heading)
            self.table.column(col, width=width)
        self.table.pack(fill=BOTH, expand=True)

        ttk.Button(right, text="🗑 Delete Selected", bootstyle="danger-outline",
                   command=self._delete_selected).pack(anchor=E, pady=8)

    def _pick_photos(self):
        paths = filedialog.askopenfilenames(
            title="Select student photos",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        self.photo_paths = list(paths)[:5]
        # Show thumbnails
        for w in self.photo_strip.winfo_children():
            w.destroy()
        for path in self.photo_paths:
            img = Image.open(path).resize((56, 56))
            tk_img = ImageTk.PhotoImage(img)
            lbl = ttk.Label(self.photo_strip, image=tk_img)
            lbl.image = tk_img
            lbl.pack(side=LEFT, padx=2)

    def _submit(self):
        name = self.vars["name"].get().strip()
        reg_no = self.vars["reg_no"].get().strip()
        dept = self.vars["dept"].get().strip()

        if not all([name, reg_no, dept]):
            messagebox.showerror("Error", "All fields are required.")
            return
        if not self.photo_paths:
            messagebox.showerror("Error", "Please select at least one photo.")
            return

        try:
            sid = register_student(name, reg_no, dept, self.photo_paths)
            messagebox.showinfo("Success", f"Student '{name}' registered (ID: {sid})")
            for var in self.vars.values():
                var.set("")
            self.photo_paths = []
            for w in self.photo_strip.winfo_children():
                w.destroy()
            self._refresh_table()
        except Exception as e:
            messagebox.showerror("Registration Failed", str(e))

    def _refresh_table(self):
        self.table.delete(*self.table.get_children())
        for s in get_all_students():
            self.table.insert("", END, iid=s["id"], values=(
                s["reg_no"], s["name"], s["department"],
                str(s["created_at"])[:10]
            ))

    def _delete_selected(self):
        selected = self.table.selection()
        if not selected:
            return
        if messagebox.askyesno("Confirm", "Delete selected student(s)? This cannot be undone."):
            for iid in selected:
                delete_student(int(iid))
            self._refresh_table()
