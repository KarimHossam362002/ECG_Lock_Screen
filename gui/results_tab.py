"""
results_tab.py
--------------
Results & Comparison tab – shows accuracy table for all classifiers/wavelets.
"""

import tkinter as tk
from tkinter import ttk

BG       = "#0d1117"
BG_PANEL = "#161b22"
ACCENT   = "#238636"
TEXT     = "#e6edf3"
DIM      = "#8b949e"
BORDER   = "#30363d"
GOLD     = "#e3b341"
RED      = "#da3633"


class ResultsTab:
    def __init__(self, parent, app):
        self.app   = app
        self.frame = ttk.Frame(parent)
        self._build()

    def _build(self):
        tk.Label(self.frame,
                 text="CLASSIFICATION RESULTS & COMPARISON",
                 bg=BG, fg=ACCENT,
                 font=("Consolas", 12, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        ttk.Separator(self.frame, orient="horizontal").pack(fill="x", padx=16, pady=4)

        # Summary cards row
        self.cards_frame = tk.Frame(self.frame, bg=BG)
        self.cards_frame.pack(fill="x", padx=16, pady=8)

        self._make_card(self.cards_frame, "Best Classifier", "—", "best_clf")
        self._make_card(self.cards_frame, "Best Accuracy",   "—", "best_acc")
        self._make_card(self.cards_frame, "Best Wavelet",    "—", "best_wav")
        self._make_card(self.cards_frame, "Best Params",     "—", "best_par")

        ttk.Separator(self.frame, orient="horizontal").pack(fill="x", padx=16, pady=4)

        # ── Main comparison table ──────────────────────────────
        table_outer = tk.Frame(self.frame, bg=BG)
        table_outer.pack(fill="both", expand=True, padx=16, pady=8)

        cols = ("Classifier", "Params", "Wavelet",
                "Train Acc", "Test Acc", "★ Best")
        self.tree = ttk.Treeview(table_outer, columns=cols,
                                 show="headings", selectmode="browse")

        widths = [110, 280, 70, 90, 90, 60]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(table_outer, orient="vertical",
                             command=self.tree.yview)
        hsb = ttk.Scrollbar(table_outer, orient="horizontal",
                             command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set,
                            xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_outer.rowconfigure(0, weight=1)
        table_outer.columnconfigure(0, weight=1)

        # colour tags
        self.tree.tag_configure("best",  background="#0d2818", foreground=ACCENT)
        self.tree.tag_configure("even",  background=BG_PANEL)
        self.tree.tag_configure("odd",   background="#0d1117")

        # Placeholder
        self.tree.insert("", "end", values=(
            "—", "Train a model first", "—", "—", "—", "—"))

    def _make_card(self, parent, title, value, key):
        card = tk.Frame(parent, bg=BG_PANEL,
                        padx=14, pady=10,
                        highlightbackground=BORDER,
                        highlightthickness=1)
        card.pack(side="left", expand=True, fill="x", padx=6)
        tk.Label(card, text=title, bg=BG_PANEL,
                 fg=DIM, font=("Consolas", 8)).pack()
        lbl = tk.Label(card, text=value, bg=BG_PANEL,
                       fg=TEXT, font=("Consolas", 12, "bold"))
        lbl.pack()
        setattr(self, f"_card_{key}", lbl)

    # ── Populate after training ───────────────────────────────

    def populate(self, training_results):
        # Clear old rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        br = training_results.best_overall
        best_key = id(br)

        # Update summary cards
        self._card_best_clf.configure(text=br.classifier_name)
        self._card_best_acc.configure(
            text=f"{br.test_acc:.1%}", fg=ACCENT)
        wavelet = br.wavelet if br.wavelet else "db4"
        self._card_best_wav.configure(text=wavelet)
        # Compact params
        p = ", ".join(f"{k}={v}" for k, v in br.params.items())
        self._card_best_par.configure(text=p[:30])

        # Populate table
        for i, r in enumerate(training_results.results):
            is_best = (r is br)
            tag  = "best" if is_best else ("even" if i % 2 == 0 else "odd")
            star = "★" if is_best else ""
            params_str = ", ".join(f"{k}={v}" for k, v in r.params.items())
            self.tree.insert("", "end", tags=(tag,), values=(
                r.classifier_name,
                params_str,
                r.wavelet,
                f"{r.train_acc:.2%}",
                f"{r.test_acc:.2%}",
                star,
            ))

        # Also add wavelet comparison summary rows
        self.tree.insert("", "end",
                         values=("─"*10,)*6, tags=("odd",))
        self.tree.insert("", "end",
                         values=("BEST PER CLASS", "", "", "", "", ""),
                         tags=("even",))
        for name, r in training_results.best_per_classifier.items():
            p = ", ".join(f"{k}={v}" for k, v in r.params.items())
            self.tree.insert("", "end", tags=("even",), values=(
                f"  {r.classifier_name}",
                p,
                r.wavelet,
                f"{r.train_acc:.2%}",
                f"{r.test_acc:.2%}",
                "",
            ))
