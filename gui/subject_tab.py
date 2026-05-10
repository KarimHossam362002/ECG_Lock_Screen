"""
subject_tab.py
--------------
Subject Manager tab: assign a photo to each subject.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import os

BG       = "#0d1117"
BG_PANEL = "#161b22"
ACCENT   = "#238636"
TEXT     = "#e6edf3"
DIM      = "#8b949e"
BORDER   = "#30363d"

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

THUMB = 100   # thumbnail size px


class SubjectTab:
    def __init__(self, parent, app):
        self.app    = app
        self.frame  = ttk.Frame(parent)
        self._cards = {}   # { subject_name: card_dict }
        self._build()

    def _build(self):
        tk.Label(self.frame,
                 text="SUBJECT PHOTO MANAGER",
                 bg=BG, fg=ACCENT,
                 font=("Consolas", 12, "bold")).pack(anchor="w",
                                                     padx=16, pady=(14, 2))
        tk.Label(self.frame,
                 text="Assign one photo per subject.  "
                      "The photo is displayed on the Lock Screen when that subject is identified.",
                 bg=BG, fg=DIM,
                 font=("Consolas", 8)).pack(anchor="w", padx=16)
        ttk.Separator(self.frame, orient="horizontal").pack(fill="x",
                                                            padx=16, pady=6)

        # Scroll canvas for subject cards
        container = tk.Frame(self.frame, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=8)

        self.canvas_scroll = tk.Canvas(container, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient="vertical",
                            command=self.canvas_scroll.yview)
        self.canvas_scroll.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas_scroll.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas_scroll, bg=BG)
        self._win_id = self.canvas_scroll.create_window(
            (0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas_scroll.configure(
                            scrollregion=self.canvas_scroll.bbox("all")))

        # Placeholder
        self._placeholder = tk.Label(self.inner,
                                     text="Train a model first to populate subjects.",
                                     bg=BG, fg=DIM,
                                     font=("Consolas", 10))
        self._placeholder.pack(pady=40)

    # ── Build cards once subjects are known ───────────────────

    def _build_cards(self, subject_names: list):
        # Clear old
        for w in self.inner.winfo_children():
            w.destroy()
        self._cards.clear()

        for i, name in enumerate(subject_names):
            card = self._make_card(self.inner, name, i)
            card["frame"].grid(row=i // 4, column=i % 4,
                               padx=10, pady=10, sticky="n")
            self._cards[name] = card

    def _make_card(self, parent, name: str, idx: int) -> dict:
        frame = tk.Frame(parent, bg=BG_PANEL, padx=10, pady=10,
                         highlightbackground=BORDER,
                         highlightthickness=1)

        # Thumbnail canvas
        cv = tk.Canvas(frame, width=THUMB, height=THUMB,
                       bg="#21262d", highlightthickness=0)
        cv.pack()
        self._draw_avatar(cv, name)

        tk.Label(frame, text=name[:18],
                 bg=BG_PANEL, fg=TEXT,
                 font=("Consolas", 9, "bold")).pack(pady=(6, 2))

        path_var = tk.StringVar(value="No photo")
        tk.Label(frame, textvariable=path_var,
                 bg=BG_PANEL, fg=DIM,
                 font=("Consolas", 7),
                 wraplength=120).pack()

        btn = ttk.Button(frame, text="📷 Assign Photo",
                         style="Ghost.TButton",
                         command=lambda n=name, pv=path_var,
                                        c=cv: self._assign_photo(n, pv, c))
        btn.pack(pady=4)

        return dict(frame=frame, canvas=cv, path_var=path_var)

    def _draw_avatar(self, cv, name: str):
        cv.delete("all")
        # Colour based on name hash
        colours = ["#1f6feb", "#238636", "#a371f7", "#f78166",
                   "#e3b341", "#39d353", "#f0883e", "#58a6ff"]
        col = colours[abs(hash(name)) % len(colours)]
        cv.create_rectangle(0, 0, THUMB, THUMB, fill="#21262d", outline="")
        cv.create_oval(25, 10, 75, 60, fill=col, outline="")
        cv.create_text(THUMB//2, THUMB//2 + 20,
                       text=name[:2].upper(),
                       fill="#ffffff",
                       font=("Consolas", 18, "bold"))

    def _assign_photo(self, name: str, path_var: tk.StringVar,
                      cv: tk.Canvas):
        path = filedialog.askopenfilename(
            title=f"Select photo for {name}",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"),
                       ("All", "*.*")]
        )
        if not path:
            return
        self.app.subject_photos[name] = path
        path_var.set(os.path.basename(path))

        if PIL_OK:
            img   = Image.open(path).resize((THUMB, THUMB), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            cv.delete("all")
            cv.create_image(0, 0, anchor="nw", image=photo)
            cv._photo = photo   # prevent GC

    # ── Called by app after training ──────────────────────────

    def on_subjects_ready(self, subject_names: list):
        self._build_cards(subject_names)
