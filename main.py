"""
ECG-Based Personal Photo Lock
HCI Project - Idea 4
Author: [Your Team Names Here]

Requirements:
    pip install numpy scipy pywavelets scikit-learn Pillow matplotlib wfdb

Dataset: PTB Database (https://physionet.org/content/ptbdb/1.0.0/)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os

# ─────────────────────────────────────────────────────────────
#  ENTRY POINT  ─  loads either real data or demo data
# ─────────────────────────────────────────────────────────────
from gui.app import ECGPhotoLockApp


if __name__ == "__main__":
    root = tk.Tk()
    app = ECGPhotoLockApp(root)
    root.mainloop()
