"""
ecg_viewer_tab.py
-----------------
ECG Viewer tab: plot raw + preprocessed signal with detected R-peaks.
Uses matplotlib embedded in tkinter.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np

BG       = "#0d1117"
BG_PANEL = "#161b22"
ACCENT   = "#238636"
TEXT     = "#e6edf3"
DIM      = "#8b949e"
BORDER   = "#30363d"

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import (
        FigureCanvasTkAgg, NavigationToolbar2Tk)
    MPL_OK = True
except ImportError:
    MPL_OK = False


class ECGViewerTab:
    def __init__(self, parent, app):
        self.app   = app
        self.frame = ttk.Frame(parent)
        self._raw_signals  = {}
        self._subject_list = []
        self._build()

    def _build(self):
        # Controls row
        ctrl = tk.Frame(self.frame, bg=BG_PANEL, height=50)
        ctrl.pack(fill="x")
        ctrl.pack_propagate(False)

        tk.Label(ctrl, text="Subject:",
                 bg=BG_PANEL, fg=TEXT,
                 font=("Consolas", 10)).pack(side="left", padx=12, pady=12)
        self.subject_var = tk.StringVar(value="—")
        self.subject_cb  = ttk.Combobox(ctrl, textvariable=self.subject_var,
                                        state="readonly", width=22,
                                        font=("Consolas", 10))
        self.subject_cb.pack(side="left", padx=6)
        self.subject_cb.bind("<<ComboboxSelected>>", lambda _: self._plot())

        tk.Label(ctrl, text="View:",
                 bg=BG_PANEL, fg=TEXT,
                 font=("Consolas", 10)).pack(side="left", padx=(14, 4))
        self.view_var = tk.StringVar(value="Both")
        for v in ["Raw", "Filtered", "Both"]:
            tk.Radiobutton(ctrl, text=v,
                           variable=self.view_var, value=v,
                           bg=BG_PANEL, fg=TEXT,
                           selectcolor=BG,
                           activebackground=BG_PANEL,
                           font=("Consolas", 9),
                           command=self._plot).pack(side="left", padx=4)

        ttk.Button(ctrl, text="⟳ Refresh",
                   command=self._plot,
                   style="Ghost.TButton").pack(side="right", padx=12)

        # Plot area
        if MPL_OK:
            self._build_mpl()
        else:
            tk.Label(self.frame,
                     text="Install matplotlib to use the ECG viewer:\n"
                          "    pip install matplotlib",
                     bg=BG, fg=DIM,
                     font=("Consolas", 11)).pack(expand=True)

    def _build_mpl(self):
        self.fig = Figure(figsize=(10, 5), dpi=96,
                          facecolor=BG_PANEL)
        self.fig.subplots_adjust(hspace=0.4)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar_frame = tk.Frame(self.frame, bg=BG_PANEL)
        toolbar_frame.pack(fill="x")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        self._draw_placeholder()

    def _draw_placeholder(self):
        if not MPL_OK:
            return
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(BG)
        ax.set_title("Train a model to visualise ECG signals",
                     color=DIM, fontsize=10, fontfamily="monospace")
        ax.tick_params(colors=DIM)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        self.canvas.draw()

    def _plot(self):
        if not MPL_OK or not self._raw_signals:
            return
        name = self.subject_var.get()
        if name not in self._raw_signals:
            return

        signal, fs = self._raw_signals[name]
        from ml.ecg_preprocessing import preprocess_ecg
        clean, r_peaks, _ = preprocess_ecg(signal, fs)

        t_raw   = np.arange(len(signal)) / fs
        t_clean = np.arange(len(clean))  / fs

        # Limit to first 5 seconds for readability
        max_t   = 5.0
        raw_end  = min(len(signal), int(max_t * fs))
        cln_end  = min(len(clean),  int(max_t * fs))
        r_vis    = r_peaks[r_peaks < cln_end]

        view = self.view_var.get()

        self.fig.clear()
        n_rows = 2 if view == "Both" else 1
        axes = self.fig.subplots(n_rows, 1)
        if n_rows == 1:
            axes = [axes]

        def _style_ax(ax, title):
            ax.set_facecolor(BG)
            ax.set_title(title, color=DIM,
                         fontsize=9, fontfamily="monospace", loc="left")
            ax.tick_params(colors=DIM, labelsize=7)
            for sp in ax.spines.values():
                sp.set_edgecolor(BORDER)
            ax.set_xlabel("Time (s)", color=DIM, fontsize=8)
            ax.set_ylabel("Amplitude", color=DIM, fontsize=8)

        row = 0
        if view in ("Raw", "Both"):
            axes[row].plot(t_raw[:raw_end], signal[:raw_end],
                           color="#1f6feb", linewidth=0.7, alpha=0.9)
            _style_ax(axes[row], f"Raw ECG — {name}")
            row += 1

        if view in ("Filtered", "Both"):
            axes[row].plot(t_clean[:cln_end], clean[:cln_end],
                           color=ACCENT, linewidth=0.7, alpha=0.9,
                           label="Filtered")
            if len(r_vis):
                axes[row].scatter(r_vis / fs, clean[r_vis],
                                  color="#ff7b72", s=24, zorder=5,
                                  label="R-peaks")
                axes[row].legend(facecolor=BG_PANEL, edgecolor=BORDER,
                                 labelcolor=TEXT, fontsize=7)
            _style_ax(axes[row], f"Filtered ECG + R-peaks — {name}")

        self.fig.patch.set_facecolor(BG_PANEL)
        self.canvas.draw()

    # ── Called by app ─────────────────────────────────────────

    def on_data_ready(self, raw_signals: dict, subject_names: list):
        self._raw_signals  = raw_signals
        self._subject_list = subject_names
        self.subject_cb.configure(values=subject_names)
        if subject_names:
            self.subject_var.set(subject_names[0])
            self._plot()
