"""
app.py
------
Main application window for ECG-Based Personal Photo Lock.
Uses tkinter with ttk styling.

Tabs:
  1. Home / Lock Screen    – photo display + identification result
  2. Training              – load data, train classifiers, see progress
  3. Results & Comparison  – accuracy table for all classifiers / wavelets
  4. ECG Viewer            – plot raw + preprocessed signal with R-peaks
  5. Subject Manager       – assign photos to subjects
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys

# Make project root importable when run from any working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.lock_tab       import LockTab
from gui.training_tab   import TrainingTab
from gui.results_tab    import ResultsTab
from gui.ecg_viewer_tab import ECGViewerTab
from gui.subject_tab    import SubjectTab

APP_TITLE  = "ECG Personal Photo Lock"
WIN_WIDTH  = 1100
WIN_HEIGHT = 720
BG_DARK    = "#0d1117"
BG_PANEL   = "#161b22"
ACCENT     = "#238636"
TEXT_MAIN  = "#e6edf3"
TEXT_DIM   = "#8b949e"
BORDER     = "#30363d"
FONT_TITLE = ("Consolas", 14, "bold")
FONT_BODY  = ("Consolas", 10)


class ECGPhotoLockApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._configure_root()
        self._apply_theme()
        self._build_ui()

        # Shared application state ─────────────────────────────
        self.training_results = None   # ml.training_engine.TrainingResults
        self.subject_names    = []
        self.subject_photos   = {}     # { name: PIL.Image or path }
        self.raw_signals      = {}     # { name: (signal, fs) }

    # ── Root window ───────────────────────────────────────────

    def _configure_root(self):
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}")
        self.root.resizable(True, True)
        self.root.configure(bg=BG_DARK)
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - WIN_WIDTH)  // 2
        y = (self.root.winfo_screenheight() - WIN_HEIGHT) // 2
        self.root.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}+{x}+{y}")

    # ── ttk Theme ─────────────────────────────────────────────

    def _apply_theme(self):
        style = ttk.Style(self.root)
        style.theme_use("default")

        style.configure(".",
                         background=BG_DARK,
                         foreground=TEXT_MAIN,
                         font=FONT_BODY,
                         borderwidth=0)

        # Notebook (tabs)
        style.configure("TNotebook",
                         background=BG_DARK,
                         borderwidth=0,
                         tabmargins=[0, 0, 0, 0])
        style.configure("TNotebook.Tab",
                         background=BG_PANEL,
                         foreground=TEXT_DIM,
                         padding=[14, 6],
                         font=("Consolas", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", BG_DARK)],
                  foreground=[("selected", ACCENT)])

        # Frame
        style.configure("TFrame", background=BG_DARK)
        style.configure("Panel.TFrame", background=BG_PANEL)

        # Label
        style.configure("TLabel",
                         background=BG_DARK,
                         foreground=TEXT_MAIN,
                         font=FONT_BODY)
        style.configure("Dim.TLabel",
                         background=BG_DARK,
                         foreground=TEXT_DIM)
        style.configure("Title.TLabel",
                         background=BG_DARK,
                         foreground=TEXT_MAIN,
                         font=FONT_TITLE)
        style.configure("Accent.TLabel",
                         background=BG_DARK,
                         foreground=ACCENT,
                         font=("Consolas", 12, "bold"))

        # Button
        style.configure("TButton",
                         background=ACCENT,
                         foreground="#ffffff",
                         padding=[10, 5],
                         relief="flat",
                         font=("Consolas", 10, "bold"))
        style.map("TButton",
                  background=[("active", "#2ea043"), ("disabled", "#21262d")])

        style.configure("Ghost.TButton",
                         background=BG_PANEL,
                         foreground=TEXT_MAIN,
                         padding=[10, 5],
                         relief="flat")
        style.map("Ghost.TButton",
                  background=[("active", BORDER)])

        # Progressbar
        style.configure("TProgressbar",
                         troughcolor=BG_PANEL,
                         background=ACCENT,
                         thickness=6)

        # Treeview (table)
        style.configure("Treeview",
                         background=BG_PANEL,
                         foreground=TEXT_MAIN,
                         fieldbackground=BG_PANEL,
                         rowheight=26,
                         font=("Consolas", 9))
        style.configure("Treeview.Heading",
                         background=BORDER,
                         foreground=TEXT_MAIN,
                         font=("Consolas", 9, "bold"))
        style.map("Treeview",
                  background=[("selected", "#1f6feb")])

        # Scrollbar
        style.configure("Vertical.TScrollbar",
                         background=BG_PANEL,
                         troughcolor=BG_DARK,
                         arrowcolor=TEXT_DIM)

        # Separator
        style.configure("TSeparator", background=BORDER)

        # Combobox
        style.configure("TCombobox",
                         fieldbackground=BG_PANEL,
                         background=BG_PANEL,
                         foreground=TEXT_MAIN,
                         selectbackground="#1f6feb",
                         font=("Consolas", 10))

        # Scale
        style.configure("TScale",
                         background=BG_DARK,
                         troughcolor=BG_PANEL)

    # ── Main UI ───────────────────────────────────────────────

    def _build_ui(self):
        # ── Header bar ────────────────────────────────────────
        header = tk.Frame(self.root, bg="#010409", height=50)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header,
                 text="⬡  ECG PERSONAL PHOTO LOCK",
                 bg="#010409", fg=ACCENT,
                 font=("Consolas", 13, "bold")).pack(side="left", padx=18, pady=12)

        tk.Label(header,
                 text="HCI Project · Idea 4",
                 bg="#010409", fg=TEXT_DIM,
                 font=("Consolas", 9)).pack(side="right", padx=18)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x")

        # ── Notebook ──────────────────────────────────────────
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        # Instantiate each tab  (pass app reference for shared state)
        self.lock_tab    = LockTab(self.notebook, self)
        self.train_tab   = TrainingTab(self.notebook, self)
        self.results_tab = ResultsTab(self.notebook, self)
        self.ecg_tab     = ECGViewerTab(self.notebook, self)
        self.subject_tab = SubjectTab(self.notebook, self)

        self.notebook.add(self.lock_tab.frame,    text="  🔒  Lock Screen  ")
        self.notebook.add(self.train_tab.frame,   text="  ⚙  Training  ")
        self.notebook.add(self.results_tab.frame, text="  📊  Results  ")
        self.notebook.add(self.ecg_tab.frame,     text="  📈  ECG Viewer  ")
        self.notebook.add(self.subject_tab.frame, text="  👤  Subjects  ")

    # ── Shared helpers ────────────────────────────────────────

    def update_after_training(self, training_results):
        """Called by TrainingTab after training is done."""
        self.training_results = training_results
        self.subject_names    = training_results.subject_names
        self.results_tab.populate(training_results)
        self.lock_tab.on_model_ready(training_results)
        self.ecg_tab.on_data_ready(self.raw_signals, self.subject_names)
        self.subject_tab.on_subjects_ready(self.subject_names)
