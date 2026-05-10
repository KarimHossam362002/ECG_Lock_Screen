"""
training_tab.py
---------------
Training tab: load dataset, choose wavelet, launch training, show progress.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

BG       = "#0d1117"
BG_PANEL = "#161b22"
ACCENT   = "#238636"
TEXT     = "#e6edf3"
DIM      = "#8b949e"
BORDER   = "#30363d"
GOLD     = "#e3b341"


def _default_ptb_directory() -> str:
    """If PTB Diagnostic lives beside this repo (e.g. HCI/Project/physionet.org/...), use it."""
    root = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "physionet.org",
        "files",
        "ptbdb",
        "1.0.0",
    ))
    try:
        from data.dataset_loader import _looks_like_ptbdb_root
        if _looks_like_ptbdb_root(root):
            return root
    except ImportError:
        pass
    return "(Demo mode – no path needed)"


class TrainingTab:
    def __init__(self, parent, app):
        self.app   = app
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self):
        # ── Left column  (settings) ───────────────────────────
        left = tk.Frame(self.frame, bg=BG_PANEL, width=300)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="TRAINING SETTINGS",
                 bg=BG_PANEL, fg=ACCENT,
                 font=("Consolas", 11, "bold")).pack(anchor="w", padx=16, pady=(18, 4))
        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=16, pady=4)

        # Dataset path
        tk.Label(left, text="PTB Dataset Path:",
                 bg=BG_PANEL, fg=TEXT,
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=16, pady=(10, 2))

        path_frame = tk.Frame(left, bg=BG_PANEL)
        path_frame.pack(fill="x", padx=16, pady=2)
        self.data_path_var = tk.StringVar(value=_default_ptb_directory())
        tk.Entry(path_frame, textvariable=self.data_path_var,
                 bg="#21262d", fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("Consolas", 8),
                 width=24).pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="…",
                   command=self._browse_dataset,
                   style="Ghost.TButton",
                   width=3).pack(side="left", padx=2)

        # Wavelet
        tk.Label(left, text="Mother Wavelet:",
                 bg=BG_PANEL, fg=TEXT,
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        self.wavelet_var = tk.StringVar(value="db4")
        for w in ["db1", "db2", "db4"]:
            tk.Radiobutton(left, text=f"  {w}",
                           variable=self.wavelet_var, value=w,
                           bg=BG_PANEL, fg=TEXT, selectcolor=BG,
                           activebackground=BG_PANEL, activeforeground=ACCENT,
                           font=("Consolas", 10)).pack(anchor="w", padx=24)

        # Number of subjects
        tk.Label(left, text="Subjects (1-5):",
                 bg=BG_PANEL, fg=TEXT,
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        self.n_subjects_var = tk.IntVar(value=5)
        ttk.Spinbox(left, from_=1, to=5,
                    textvariable=self.n_subjects_var,
                    width=6, font=("Consolas", 10)).pack(anchor="w", padx=24)

        # Test split
        tk.Label(left, text="Test Split:",
                 bg=BG_PANEL, fg=TEXT,
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        self.split_var = tk.DoubleVar(value=0.3)
        split_frame = tk.Frame(left, bg=BG_PANEL)
        split_frame.pack(fill="x", padx=16)
        self.split_lbl = tk.Label(split_frame, text="30%",
                                  bg=BG_PANEL, fg=GOLD,
                                  font=("Consolas", 9))
        self.split_lbl.pack(side="right")
        ttk.Scale(split_frame, from_=0.1, to=0.5,
                  variable=self.split_var,
                  command=self._update_split_label).pack(fill="x", expand=True)

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=16, pady=16)

        # Train button
        self.train_btn = ttk.Button(left, text="▶  START TRAINING",
                                    command=self._start_training)
        self.train_btn.pack(padx=16, ipadx=10, ipady=6)

        # Status
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(left, textvariable=self.status_var,
                 bg=BG_PANEL, fg=DIM,
                 font=("Consolas", 8),
                 wraplength=260).pack(padx=16, pady=8)

        # ── Right column  (log + progress) ────────────────────
        right = tk.Frame(self.frame, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        tk.Label(right, text="TRAINING LOG",
                 bg=BG, fg=ACCENT,
                 font=("Consolas", 11, "bold")).pack(anchor="w")
        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=6)

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(right,
                                            variable=self.progress_var,
                                            maximum=100, length=600)
        self.progress_bar.pack(fill="x", pady=4)

        self.progress_lbl = tk.Label(right, text="",
                                     bg=BG, fg=DIM,
                                     font=("Consolas", 8))
        self.progress_lbl.pack(anchor="w")

        # Log text
        log_outer = tk.Frame(right, bg=BG_PANEL, bd=1, relief="sunken")
        log_outer.pack(fill="both", expand=True, pady=8)

        self.log_text = tk.Text(log_outer, bg=BG_PANEL, fg=DIM,
                                font=("Consolas", 8),
                                state="disabled", wrap="word", bd=0)
        sc = ttk.Scrollbar(log_outer, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

        self._log("Configure settings and press START TRAINING.")
        self._log("The tool will use demo data if no PTB path is provided.")

    def _browse_dataset(self):
        path = filedialog.askdirectory(title="Select PTB Dataset Root Folder")
        if path:
            self.data_path_var.set(path)

    def _update_split_label(self, _val=None):
        self.split_lbl.configure(text=f"{self.split_var.get():.0%}")

    def _log(self, msg: str, color: str = None):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"▸  {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _progress_cb(self, msg: str, step: int, total: int):
        pct = (step / max(total, 1)) * 100
        self.frame.after(0, lambda: self._update_progress(msg, pct))

    def _update_progress(self, msg: str, pct: float):
        self.progress_var.set(pct)
        self.progress_lbl.configure(text=msg)
        self._log(msg)

    def _start_training(self):
        self.train_btn.configure(state="disabled")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.status_var.set("Training in progress …")
        self.progress_var.set(0)
        self._log("Loading dataset …")

        threading.Thread(target=self._training_worker, daemon=True).start()

    def _training_worker(self):
        try:
            from data.dataset_loader import load_ptb_dataset
            from ml.feature_extraction import WAVELETS
            from ml.training_engine import train_wavelet_comparison

            data_dir   = self.data_path_var.get()
            n_subjects = self.n_subjects_var.get()
            test_size  = self.split_var.get()

            self.frame.after(0, lambda: self._log("Preprocessing ECG signals …"))

            datasets_by_wavelet = {}
            subject_names = None
            raw_signals = None

            for wavelet in WAVELETS:
                load_msg = f"Extracting {wavelet} wavelet features ..."
                self.frame.after(0, lambda m=load_msg: self._log(m))
                (X_train, X_test,
                 y_train, y_test,
                 current_subject_names,
                 current_raw_signals) = load_ptb_dataset(
                    data_dir,
                    n_subjects=n_subjects,
                    wavelet=wavelet,
                    test_size=test_size
                )
                datasets_by_wavelet[wavelet] = (X_train, X_test, y_train, y_test)
                if subject_names is None:
                    subject_names = current_subject_names
                    raw_signals = current_raw_signals

            # Store raw signals in the app for ECG viewer
            self.app.raw_signals = raw_signals

            first_wavelet = WAVELETS[0]
            X_train, X_test, _, _ = datasets_by_wavelet[first_wavelet]
            msg = (f"Dataset loaded. "
                   f"Train: {len(X_train)}, Test: {len(X_test)} segments.")
            self.frame.after(0, lambda: self._log(msg))

            results = train_wavelet_comparison(
                datasets_by_wavelet,
                subject_names,
                progress_cb=self._progress_cb
            )

            self.frame.after(0, lambda: self._on_done(results))

        except Exception as exc:
            import traceback
            msg = str(exc)
            tb = traceback.format_exc()
            self.frame.after(0, lambda m=msg, trace=tb: self._on_error(m, trace))

    def _on_done(self, results):
        self.train_btn.configure(state="normal")
        br = results.best_overall
        self.status_var.set(f"Done! Best: {br.classifier_name} — {br.test_acc:.1%}")
        self._log("=" * 50)
        self._log("TRAINING COMPLETE")
        for name, r in results.best_per_classifier.items():
            self._log(
                f"  {name:<16} best acc: {r.test_acc:.1%}  "
                f"wavelet={r.wavelet}  {r.params}"
            )
        self._log(
            f"  Overall best: {br.classifier_name}  "
            f"wavelet={br.wavelet}  ({br.test_acc:.1%})"
        )
        self.progress_var.set(100)
        self.app.update_after_training(results)

    def _on_error(self, msg: str, tb: str):
        self.train_btn.configure(state="normal")
        self.status_var.set("Error during training.")
        self._log(f"ERROR: {msg}")
        self._log(tb)
