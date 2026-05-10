"""
lock_tab.py
-----------
Lock Screen tab:  the photo lock authentication interface.

States:
  • LOCKED   – shows a padlock, "Scan ECG to Unlock"
  • SCANNING – shows progress bar while classifier runs
  • UNLOCKED – shows identified subject photo + name
  • DENIED   – shows "Unidentified" warning
"""

import tkinter as tk
from tkinter import ttk, filedialog
import threading
import os
import numpy as np

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

BG         = "#0d1117"
BG_PANEL   = "#161b22"
ACCENT     = "#238636"
RED        = "#da3633"
GOLD       = "#e3b341"
TEXT       = "#e6edf3"
DIM        = "#8b949e"
BORDER     = "#30363d"


class LockTab:
    def __init__(self, parent, app):
        self.app   = app
        self.frame = ttk.Frame(parent)
        self._model_ready = False
        self._build()

    # ── Layout ────────────────────────────────────────────────

    def _build(self):
        root_frame = self.frame

        # ── Left panel  (photo / status) ──────────────────────
        left = tk.Frame(root_frame, bg=BG_PANEL, width=380)
        left.pack(side="left", fill="y", padx=0)
        left.pack_propagate(False)

        # Photo canvas
        self.photo_canvas = tk.Canvas(left, width=340, height=340,
                                      bg="#0d1117", highlightthickness=1,
                                      highlightbackground=BORDER)
        self.photo_canvas.pack(pady=(30, 10), padx=20)

        self._draw_lock_placeholder()

        # Subject name
        self.name_var = tk.StringVar(value="—  Not Identified  —")
        tk.Label(left, textvariable=self.name_var,
                 bg=BG_PANEL, fg=TEXT,
                 font=("Consolas", 13, "bold")).pack(pady=(4, 2))

        # Confidence
        self.conf_var = tk.StringVar(value="")
        tk.Label(left, textvariable=self.conf_var,
                 bg=BG_PANEL, fg=DIM,
                 font=("Consolas", 9)).pack(pady=(0, 10))

        # Status badge
        self.status_var = tk.StringVar(value="LOCKED")
        self.status_lbl = tk.Label(left, textvariable=self.status_var,
                                   bg=BG_PANEL, fg=GOLD,
                                   font=("Consolas", 11, "bold"))
        self.status_lbl.pack(pady=4)

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # Progress bar (hidden until scan)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(left, variable=self.progress_var,
                                            maximum=100, mode="indeterminate",
                                            length=300)
        self.progress_bar.pack(pady=4, padx=20)

        # ── Right panel  (controls) ───────────────────────────
        right = tk.Frame(root_frame, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        tk.Label(right, text="AUTHENTICATION CONSOLE",
                 bg=BG, fg=ACCENT,
                 font=("Consolas", 12, "bold")).pack(anchor="w", pady=(10, 2))
        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=6)

        # ECG source selection
        src_frame = tk.Frame(right, bg=BG)
        src_frame.pack(fill="x", pady=8)

        tk.Label(src_frame, text="ECG Signal Source:",
                 bg=BG, fg=TEXT,
                 font=("Consolas", 10, "bold")).pack(anchor="w")

        self.source_var = tk.StringVar(value="Demo (random)")
        sources = ["Demo (random)", "Load ECG file (.npy / .csv)"]
        self.source_combo = ttk.Combobox(src_frame, textvariable=self.source_var,
                                         values=sources, state="readonly",
                                         width=35)
        self.source_combo.pack(anchor="w", pady=4)
        self.source_combo.bind("<<ComboboxSelected>>", self._on_source_change)

        self.file_btn = ttk.Button(src_frame, text="📂  Browse ECG file",
                                   command=self._browse_file,
                                   style="Ghost.TButton")
        self.file_path_var = tk.StringVar(value="No file selected")
        self.file_lbl = tk.Label(src_frame, textvariable=self.file_path_var,
                                 bg=BG, fg=DIM, font=("Consolas", 8),
                                 wraplength=400)

        # Scan button
        self.scan_btn = ttk.Button(right, text="▶  SCAN ECG  ▶",
                                   command=self._start_scan,
                                   state="disabled")
        self.scan_btn.pack(pady=16, ipadx=20, ipady=6)

        # Reset button
        ttk.Button(right, text="⟳  Reset Lock",
                   command=self._reset,
                   style="Ghost.TButton").pack(pady=4)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=12)

        # Log
        tk.Label(right, text="System Log:",
                 bg=BG, fg=DIM,
                 font=("Consolas", 9, "bold")).pack(anchor="w")

        log_frame = tk.Frame(right, bg=BG_PANEL, bd=1, relief="sunken")
        log_frame.pack(fill="both", expand=True, pady=6)

        self.log_text = tk.Text(log_frame, bg=BG_PANEL, fg=DIM,
                                font=("Consolas", 8),
                                state="disabled", wrap="word",
                                height=10, bd=0)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

        self._log("System initialised. Train a model first.")

    # ── Placeholder ───────────────────────────────────────────

    def _draw_lock_placeholder(self):
        c = self.photo_canvas
        c.delete("all")
        c.create_rectangle(0, 0, 340, 340, fill="#0d1117", outline="")
        # Draw lock icon with canvas shapes
        cx, cy = 170, 160
        # shackle arc
        c.create_arc(cx-40, cy-80, cx+40, cy,
                     start=0, extent=180,
                     outline=BORDER, width=12, style="arc")
        # body
        c.create_rectangle(cx-55, cy-10, cx+55, cy+70,
                            fill=BG_PANEL, outline=BORDER, width=2)
        # keyhole
        c.create_oval(cx-12, cy+10, cx+12, cy+34,
                      fill=BG, outline=BORDER, width=1)
        c.create_rectangle(cx-6, cy+28, cx+6, cy+50,
                            fill=BG, outline="")
        c.create_text(cx, cy+100, text="LOCKED",
                      fill=GOLD, font=("Consolas", 11, "bold"))

    def _draw_unlock(self):
        c = self.photo_canvas
        c.delete("all")
        c.create_rectangle(0, 0, 340, 340, fill="#0d1117", outline="")
        cx, cy = 170, 160
        c.create_rectangle(cx-55, cy-10, cx+55, cy+70,
                            fill=BG_PANEL, outline=ACCENT, width=2)
        c.create_text(cx, cy+100, text="UNLOCKED",
                      fill=ACCENT, font=("Consolas", 11, "bold"))

    # ── Source helpers ────────────────────────────────────────

    def _on_source_change(self, _event=None):
        if "file" in self.source_var.get().lower():
            self.file_btn.pack(anchor="w", pady=4)
            self.file_lbl.pack(anchor="w")
        else:
            self.file_btn.pack_forget()
            self.file_lbl.pack_forget()

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select ECG file",
            filetypes=[("NumPy", "*.npy"), ("CSV", "*.csv"), ("All", "*.*")]
        )
        if path:
            self.file_path_var.set(os.path.basename(path))
            self._ecg_file = path

    # ── Scan ──────────────────────────────────────────────────

    def _start_scan(self):
        if not self._model_ready:
            messagebox.showwarning("No Model", "Please train a model first.")
            return

        self.scan_btn.configure(state="disabled")
        self.status_var.set("SCANNING …")
        self.status_lbl.configure(fg=GOLD)
        self.name_var.set("Analysing ECG signal …")
        self.conf_var.set("")
        self.progress_bar.start(12)
        self._log("Starting ECG scan …")

        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        import numpy as np
        try:
            source = self.source_var.get()
            tr = self.app.training_results
            br = tr.best_overall

            if "file" in source.lower() and hasattr(self, "_ecg_file"):
                path = self._ecg_file
                if path.endswith(".npy"):
                    signal = np.load(path)
                else:
                    signal = np.loadtxt(path, delimiter=",")
                if signal.ndim > 1:
                    signal = signal[:, 0]
                fs = 1000.0
            else:
                # Demo: pick a subject's stored signal
                names = tr.subject_names
                chosen = names[np.random.randint(len(names))]
                signal, fs = self.app.raw_signals.get(chosen,
                                (np.random.randn(5000), 1000.0))
                self._log(f"Demo: using signal for {chosen}")

            from ml.training_engine import run_identification
            identity, confidence = run_identification(
                br, signal, fs, tr.subject_names
            )
            self.frame.after(0, lambda: self._show_result(identity, confidence))

        except Exception as exc:
            msg = str(exc)
            self.frame.after(0, lambda m=msg: self._show_error(m))

    def _show_result(self, identity: str, confidence: float):
        self.progress_bar.stop()
        self.progress_var.set(0)
        self.scan_btn.configure(state="normal")

        if identity == "Unidentified":
            self._set_denied(confidence)
        else:
            self._set_unlocked(identity, confidence)

    def _show_error(self, msg: str):
        self.progress_bar.stop()
        self.scan_btn.configure(state="normal")
        self.status_var.set("ERROR")
        self.status_lbl.configure(fg=RED)
        self._log(f"Error: {msg}")
        messagebox.showerror("Scan Error", msg)

    def _set_unlocked(self, name: str, confidence: float):
        self.status_var.set("UNLOCKED ✔")
        self.status_lbl.configure(fg=ACCENT)
        self.name_var.set(name)
        self.conf_var.set(f"Confidence: {confidence:.1%}")
        self._log(f"Identified: {name}  ({confidence:.1%})")

        # Show photo if available
        photo_path = self.app.subject_photos.get(name)
        if PIL_OK and photo_path and os.path.isfile(str(photo_path)):
            self._show_photo(photo_path)
        else:
            self._draw_unlock()
            c = self.photo_canvas
            c.create_text(170, 200, text=name[:20],
                          fill=ACCENT, font=("Consolas", 16, "bold"))

    def _set_denied(self, confidence: float):
        self.status_var.set("ACCESS DENIED ✗")
        self.status_lbl.configure(fg=RED)
        self.name_var.set("UNIDENTIFIED")
        self.conf_var.set(f"Max confidence: {confidence:.1%}  (< 80%)")
        self._log(f"Access denied. Confidence: {confidence:.1%}")
        c = self.photo_canvas
        c.delete("all")
        c.create_rectangle(0, 0, 340, 340, fill="#0d1117", outline="")
        c.create_text(170, 170, text="✗\nACCESS\nDENIED",
                      fill=RED, font=("Consolas", 18, "bold"),
                      justify="center")

    def _show_photo(self, path: str):
        img = Image.open(path).resize((340, 340), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.photo_canvas.delete("all")
        self.photo_canvas.create_image(0, 0, anchor="nw", image=photo)
        # keep reference
        self.photo_canvas._photo = photo
        # overlay name
        self.photo_canvas.create_rectangle(0, 300, 340, 340,
                                           fill="#000000aa", outline="")

    def _reset(self):
        self._draw_lock_placeholder()
        self.status_var.set("LOCKED")
        self.status_lbl.configure(fg=GOLD)
        self.name_var.set("—  Not Identified  —")
        self.conf_var.set("")
        self.progress_bar.stop()
        self._log("Lock reset.")

    def _log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"▸  {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ── Called by app after training ──────────────────────────

    def on_model_ready(self, training_results):
        self._model_ready = True
        self.scan_btn.configure(state="normal")
        self.status_var.set("READY — SCAN TO UNLOCK")
        self.status_lbl.configure(fg=ACCENT)
        self._draw_lock_placeholder()
        br = training_results.best_overall
        self._log(f"Model ready. Best: {br.classifier_name} "
                  f"({br.test_acc:.1%} acc)")
        self._log("Select ECG source and press SCAN.")
